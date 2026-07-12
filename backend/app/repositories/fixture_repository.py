"""Fixture-backed repository with in-memory overlays for mutable flows."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from threading import RLock
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.calculations.confidence import apply_confidence_penalties, derive_safe_status
from app.calculations.returns import (
    build_price_reaction,
    compute_asset_return,
    compute_benchmark_return,
    compute_relative_volume,
)
from app.contracts.api import AgentRunStep, AnalysisRequest, BriefingRequest, ReviewRequest, Watchlist
from app.contracts.entities import (
    DISCLAIMER,
    AgentRun,
    AnalysisStatus,
    Article,
    Briefing,
    BriefingStatus,
    DataMode,
    DataProvenance,
    Event,
    Evidence,
    Freshness,
    HumanReviewSummary,
    Impact,
    PrioritizedSignal,
    ReviewStatus,
    ReviewSummary,
    ReviewTask,
    Reviewer,
    Signal,
    SignalReview,
    Source,
    SourceTier,
    WatchlistRef,
    allow_internal_field_names,
)
from app.contracts.fixtures import canonical_json_bytes, sha256_digest
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService
from app.repositories.base import BackendRepository


FIXTURE_WARNINGS: tuple[str, ...] = ("FIXTURE_DATA", "NOT_REAL_TIME")
PROMPT_VERSION = "backend-f1-f5-v1"
REVIEWER = {"id": "usr_analista_demo", "name": "Analista Demo"}
SOURCE_TIER_SCORES = {
    SourceTier.A: 0.92,
    SourceTier.B: 0.82,
    SourceTier.C: 0.74,
    SourceTier.D: 0.60,
}


class FixtureRepository(BackendRepository):
    """Read the canonical fixture bundle and keep mutable state in memory."""

    def __init__(
        self,
        provider: FixtureProvider,
        market_runtime: MarketDataRuntimeService | None = None,
    ) -> None:
        self._provider = provider
        self._market_runtime = market_runtime
        self._bundle = provider.load_bundle()
        self._sources = {item.id: item for item in self._bundle.sources}
        self._articles = {item.id: item for item in self._bundle.articles}
        self._events = {item.id: item for item in self._bundle.events}
        self._assets = {item.id: item for item in self._bundle.assets}
        self._assets_by_symbol = {item.symbol: item for item in self._bundle.assets}
        self._snapshots = {item.id: item for item in self._bundle.market_snapshots}
        self._claims = {item.id: item for item in self._bundle.claims}
        self._evidence = {item.id: item for item in self._bundle.evidence}
        self._signal_seeds = {item.id: item for item in self._bundle.signals}
        self._reviews_by_signal: dict[str, list[SignalReview]] = defaultdict(list)
        for review in self._bundle.signal_reviews:
            self._reviews_by_signal[review.signal_id].append(review)
        self._briefings = {item.briefing_id: item for item in self._bundle.briefings}
        self._runs = {item.id: item for item in self._bundle.agent_runs}
        self._run_steps: dict[str, list[AgentRunStep]] = defaultdict(list)
        self._analysis_idempotency: dict[str, tuple[str, bytes]] = {}
        self._review_idempotency: dict[str, tuple[str, bytes]] = {}
        self._briefing_idempotency: dict[str, tuple[str, bytes]] = {}
        self._lock = RLock()

    @property
    def fixture_clock(self) -> datetime:
        return self._bundle.manifest.fixture_clock

    def get_meta(self) -> DataProvenance:
        clock = self._bundle.manifest.fixture_clock
        if self._market_runtime is not None:
            return self._market_runtime.repository_provenance(clock)
        with allow_internal_field_names():
            freshness = Freshness(
                evaluated_at=clock,
                stale_after_seconds=86_400,
                is_stale=False,
            )
            return DataProvenance(
                data_mode=DataMode.FIXTURE,
                provider="fixture_repository",
                retrieved_at=clock,
                data_as_of=clock,
                freshness=freshness,
                warnings=FIXTURE_WARNINGS,
            )

    def list_events(
        self,
        *,
        instrument_type: str | None = None,
        asset: str | None = None,
        published_after: str | None = None,
    ) -> tuple[tuple[Event, tuple[str, ...]], ...]:
        with self._lock:
            result: list[tuple[Event, tuple[str, ...]]] = []
            for event in self._bundle.events:
                asset_symbols = tuple(relation.symbol for relation in event.related_assets)
                if instrument_type and not any(
                    self._assets[relation.asset_id].instrument_type.value == instrument_type
                    for relation in event.related_assets
                ):
                    continue
                if asset and asset not in asset_symbols:
                    continue
                if published_after and event.event_at.isoformat().replace("+00:00", "Z") <= published_after:
                    continue
                result.append((event, asset_symbols))
            return tuple(result)

    def get_event(self, event_id: str) -> tuple[Event, tuple[str, ...]]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                raise KeyError(event_id)
            asset_symbols = tuple(relation.symbol for relation in event.related_assets)
            return event, asset_symbols

    def get_watchlist(self) -> Watchlist:
        watchlist = self._bundle.briefings[0].watchlist
        asset_ids = tuple(
            self._assets_by_symbol[symbol].id for symbol in ("AAPL", "BTC-USD", "WTI")
        )
        with allow_internal_field_names():
            return Watchlist(
                id=watchlist.id,
                name=watchlist.name,
                asset_ids=asset_ids,
            )

    def list_signals(
        self,
        *,
        instrument_type: str | None = None,
        asset: str | None = None,
        published_after: str | None = None,
    ) -> tuple[Signal, ...]:
        with self._lock:
            result: list[Signal] = []
            for signal in self._signal_seeds.values():
                if instrument_type and signal.asset.instrument_type.value != instrument_type:
                    continue
                if asset and signal.asset.symbol != asset:
                    continue
                if published_after:
                    event = self._events[signal.event_id]
                    if event.event_at.isoformat().replace("+00:00", "Z") <= published_after:
                        continue
                result.append(self.build_runtime_signal(signal.id))
            return tuple(sorted(result, key=lambda signal: signal.id))

    def get_signal(self, signal_id: str) -> Signal:
        return self.build_runtime_signal(signal_id)

    def get_signal_seed(self, signal_id: str) -> Signal:
        with self._lock:
            signal = self._signal_seeds.get(signal_id)
            if signal is None:
                raise KeyError(signal_id)
            return signal

    def get_signal_evidence(self, signal_id: str) -> tuple[Evidence, ...]:
        with self._lock:
            if signal_id not in self._signal_seeds:
                raise KeyError(signal_id)
            result = tuple(item for item in self._bundle.evidence if item.signal_id == signal_id)
            return tuple(sorted(result, key=lambda item: item.id))

    def list_signal_reviews(self, signal_id: str) -> tuple[SignalReview, ...]:
        with self._lock:
            if signal_id not in self._signal_seeds:
                raise KeyError(signal_id)
            return tuple(
                sorted(self._reviews_by_signal.get(signal_id, []), key=lambda item: item.created_at)
            )

    def create_signal_review(
        self,
        signal_id: str,
        request: ReviewRequest,
        *,
        idempotency_key: str,
    ) -> tuple[SignalReview, ...]:
        with self._lock:
            signal = self.get_signal_seed(signal_id)
            payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
            previous_result = self._review_idempotency.get(idempotency_key)
            if previous_result is not None:
                previous_signal_id, previous_payload = previous_result
                if previous_signal_id != signal_id or previous_payload != payload:
                    raise ValueError("Idempotency-Key already used with a different review payload")
                return self.list_signal_reviews(signal_id)

            requested_status = ReviewStatus(request.status)
            if signal.review.status == requested_status:
                raise ValueError("Signal is already in the requested review status")

            review_index = len(self._reviews_by_signal.get(signal_id, [])) + 1
            reviewed_at = self.fixture_clock + timedelta(minutes=review_index)
            created_at = reviewed_at + timedelta(seconds=30)
            with allow_internal_field_names():
                reviewer = Reviewer(**REVIEWER)
                review = SignalReview(
                    id=f"rev_{signal_id}_{review_index:03d}",
                    signal_id=signal_id,
                    previous_status=signal.review.status,
                    status=requested_status,
                    justification=request.justification,
                    reviewed_by=reviewer,
                    reviewed_at=reviewed_at,
                    created_at=created_at,
                )
                review_summary = ReviewSummary(
                    status=requested_status,
                    justification=request.justification,
                    reviewed_by=reviewer,
                    reviewed_at=reviewed_at,
                )

            self._reviews_by_signal[signal_id].append(review)
            self._signal_seeds[signal_id] = signal.model_copy(
                update={"review": review_summary, "updated_at": created_at}
            )
            self._review_idempotency[idempotency_key] = (signal_id, payload)
            self._sync_briefings_for_signal(signal_id, updated_at=created_at)
            return self.list_signal_reviews(signal_id)

    def create_briefing(
        self,
        request: BriefingRequest,
        *,
        idempotency_key: str,
        executive_summary: str,
    ) -> Briefing:
        with self._lock:
            payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
            previous_result = self._briefing_idempotency.get(idempotency_key)
            if previous_result is not None:
                briefing_id, previous_payload = previous_result
                if previous_payload != payload:
                    raise ValueError("Idempotency-Key already used with a different briefing payload")
                return self.get_briefing(briefing_id)

            signals = tuple(self.build_runtime_signal(signal_id) for signal_id in request.signal_ids)
            if request.status == BriefingStatus.SHAREABLE:
                self._assert_shareable_signals(signals)

            created_at = self.fixture_clock + timedelta(minutes=len(self._briefings) + 10)
            briefing_id = f"brf_runtime_{len(self._briefings) + 1:03d}"
            prioritized_signals = tuple(self._build_prioritized_signal(signal) for signal in signals)
            review_tasks = self._build_review_tasks(
                signals,
                briefing_id=briefing_id,
                created_at=created_at,
            )
            effective_status = self._effective_briefing_status(request.status, signals, review_tasks)
            with allow_internal_field_names():
                briefing = Briefing(
                    briefing_id=briefing_id,
                    status=effective_status,
                    watchlist=WatchlistRef(id="watchlist_demo_global", name="Demo Global"),
                    executive_summary=executive_summary,
                    prioritized_signals=prioritized_signals,
                    review_tasks=review_tasks,
                    human_review_summary=self._build_human_review_summary(signals),
                    requires_human_review=True,
                    disclaimer=DISCLAIMER,
                    created_at=created_at,
                    updated_at=created_at,
                )
            self._briefings[briefing.briefing_id] = briefing
            self._briefing_idempotency[idempotency_key] = (briefing.briefing_id, payload)
            return briefing

    def get_briefing(self, briefing_id: str) -> Briefing:
        with self._lock:
            briefing = self._briefings.get(briefing_id)
            if briefing is None:
                raise KeyError(briefing_id)
            signal_ids = tuple(item.signal_id for item in briefing.prioritized_signals)
            signals = tuple(self.build_runtime_signal(signal_id) for signal_id in signal_ids)
            prioritized_signals = tuple(self._build_prioritized_signal(signal) for signal in signals)
            review_tasks = self._build_review_tasks(
                signals,
                briefing_id=briefing.briefing_id,
                created_at=briefing.created_at,
                existing_tasks=briefing.review_tasks,
            )
            effective_status = self._effective_briefing_status(briefing.status, signals, review_tasks)
            updated_at = max(
                [briefing.updated_at, *(signal.updated_at for signal in signals), *(filter(None, (task.resolved_at for task in review_tasks)))],
                default=briefing.updated_at,
            )
            refreshed = briefing.model_copy(
                update={
                    "status": effective_status,
                    "prioritized_signals": prioritized_signals,
                    "review_tasks": review_tasks,
                    "human_review_summary": self._build_human_review_summary(signals),
                    "updated_at": updated_at,
                }
            )
            self._briefings[briefing_id] = refreshed
            return refreshed

    def create_analysis_run(
        self,
        request: AnalysisRequest,
        *,
        idempotency_key: str,
        model_name: str,
        prompt_version: str,
    ) -> tuple[AgentRun, bool]:
        with self._lock:
            payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
            previous_result = self._analysis_idempotency.get(idempotency_key)
            if previous_result is not None:
                run_id, previous_payload = previous_result
                if previous_payload != payload:
                    raise ValueError("Idempotency-Key already used with a different analysis payload")
                return self.get_analysis_run(run_id), False

            matched_signals = self._resolve_request_signals(request)
            if not matched_signals:
                raise KeyError("No fixture signal matches the requested event and assets")

            started_at = self.fixture_clock + timedelta(minutes=len(self._runs) + 1)
            run_id = f"run_runtime_{len(self._runs) + 1:03d}"
            with allow_internal_field_names():
                run = AgentRun(
                    id=run_id,
                    organization_id="org_demo",
                    conversation_id=None,
                    current_node="scheduled",
                    status=AnalysisStatus.PROCESSING,
                    model_name=model_name,
                    prompt_version=prompt_version,
                    input_hash=sha256_digest(request.model_dump(mode="json", by_alias=True)),
                    source_snapshot_ids=self._resolve_source_snapshot_ids(matched_signals),
                    started_at=started_at,
                    finished_at=None,
                    error_code=None,
                    retry_count=0,
                )
            self._runs[run.id] = run
            self._run_steps[run.id] = []
            self._analysis_idempotency[idempotency_key] = (run.id, payload)
            return run, True

    def get_analysis_run(self, run_id: str) -> AgentRun:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            return run

    def append_run_step(self, run_id: str, step: AgentRunStep) -> None:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            steps = self._run_steps[run_id]
            if any(existing.id == step.id for existing in steps):
                return
            steps.append(step)
            self._runs[run_id] = self._runs[run_id].model_copy(update={"current_node": step.node})

    def complete_analysis_run(
        self,
        run_id: str,
        *,
        status: str,
        current_node: str,
    ) -> AgentRun:
        with self._lock:
            run = self.get_analysis_run(run_id)
            steps = self._run_steps.get(run_id, [])
            finished_at = steps[-1].timestamp if steps else run.started_at
            updated = run.model_copy(
                update={
                    "status": AnalysisStatus(status),
                    "current_node": current_node,
                    "finished_at": finished_at,
                    "error_code": None,
                }
            )
            self._runs[run_id] = updated
            return updated

    def fail_analysis_run(
        self,
        run_id: str,
        *,
        current_node: str,
        error_code: str,
    ) -> AgentRun:
        with self._lock:
            run = self.get_analysis_run(run_id)
            steps = self._run_steps.get(run_id, [])
            finished_at = steps[-1].timestamp if steps else run.started_at
            updated = run.model_copy(
                update={
                    "status": AnalysisStatus.FAILED,
                    "current_node": current_node,
                    "finished_at": finished_at,
                    "error_code": error_code,
                }
            )
            self._runs[run_id] = updated
            return updated

    def is_run_terminal(self, run_id: str) -> bool:
        return self.get_analysis_run(run_id).status != AnalysisStatus.PROCESSING

    def set_run_steps(self, run_id: str, steps: tuple[AgentRunStep, ...]) -> None:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            self._run_steps[run_id] = list(steps)

    def get_run_steps(self, run_id: str) -> tuple[AgentRunStep, ...]:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            return tuple(self._run_steps.get(run_id, []))

    def get_event_articles(self, event_id: str) -> tuple[Article, ...]:
        with self._lock:
            event = self._events[event_id]
            articles = tuple(self._articles[article_id] for article_id in event.article_ids)
            deduplicated, _ = self._deduplicate_articles(articles)
            return deduplicated

    def get_event_sources(self, event_id: str) -> tuple[Source, ...]:
        with self._lock:
            articles = self.get_event_articles(event_id)
            source_ids = {article.source_id for article in articles}
            return tuple(self._sources[source_id] for source_id in sorted(source_ids))

    def get_normalized_event_articles(self, event_id: str) -> tuple[dict[str, Any], ...]:
        articles = self.get_event_articles(event_id)
        normalized = []
        for article in articles:
            normalized.append(
                {
                    "id": article.id,
                    "headline": article.headline,
                    "sourceId": article.source_id,
                    "publishedAt": article.published_at.isoformat().replace("+00:00", "Z"),
                    "providerArticleId": article.provider_article_id,
                    "canonicalUrl": self._canonicalize_url(str(article.url)),
                    "contentHash": article.content_hash,
                    "provider": article.provider,
                    "dataMode": article.data_mode.value,
                    "dataAsOf": article.data_as_of.isoformat().replace("+00:00", "Z"),
                    "warnings": list(article.warnings),
                }
            )
        return tuple(normalized)

    def get_event_source_diagnostics(self, event_id: str) -> dict[str, Any]:
        with self._lock:
            event = self._events[event_id]
            articles = tuple(self._articles[article_id] for article_id in event.article_ids)
        deduplicated, duplicate_article_ids = self._deduplicate_articles(articles)
        sources = self.get_event_sources(event_id)
        independent_groups = self._independent_original_publisher_groups(sources)
        warnings = list(duplicate_article_ids)
        if len(independent_groups) < 2:
            warnings.append("INSUFFICIENT_INDEPENDENT_PUBLISHERS")
        if not any(source.is_original_publisher for source in sources):
            warnings.append("MISSING_ORIGINAL_PUBLISHER")
        stale_article_ids = tuple(
            article.id
            for article in deduplicated
            if article.freshness.is_stale
        )
        if stale_article_ids:
            warnings.append("STALE_EVENT_ARTICLES")
        return {
            "articleCount": len(deduplicated),
            "sourceCount": len(sources),
            "independentPublisherCount": len(independent_groups),
            "independentPublisherGroups": list(independent_groups),
            "duplicateArticleIds": list(duplicate_article_ids),
            "staleArticleIds": list(stale_article_ids),
            "warnings": warnings,
            "dataMode": self.get_meta().data_mode.value,
        }

    def get_event_market_snapshots(self, event: Event) -> tuple[Any, ...]:
        relation_asset_ids = {relation.asset_id for relation in event.related_assets}
        with self._lock:
            return tuple(
                snapshot
                for snapshot in self._bundle.market_snapshots
                if snapshot.asset_id in relation_asset_ids
            )

    def get_event_asset_relations(self, event_id: str) -> tuple[dict[str, Any], ...]:
        with self._lock:
            event = self._events[event_id]
            return tuple(
                {
                    "assetId": relation.asset_id,
                    "symbol": relation.symbol,
                    "relationship": relation.relationship,
                    "reason": relation.reason,
                    "entityMatchScore": relation.entity_match_score,
                }
                for relation in event.related_assets
            )

    def calculate_signal_price_reaction(self, signal: Signal) -> Any | None:
        event = self._events[signal.event_id]
        primary_asset = self._assets_by_symbol[signal.asset.symbol]
        asset_snapshot = next(
            snapshot
            for snapshot in self.get_event_market_snapshots(event)
            if snapshot.asset_id == primary_asset.id
        )
        benchmark_snapshot = next(
            (
                snapshot
                for snapshot in self._bundle.market_snapshots
                if primary_asset.benchmark_asset_id is not None
                and snapshot.asset_id == primary_asset.benchmark_asset_id
            ),
            None,
        )
        return build_price_reaction(
            asset_return=compute_asset_return(asset_snapshot),
            benchmark_return=compute_benchmark_return(
                asset_snapshot=asset_snapshot,
                benchmark_snapshot=benchmark_snapshot,
            ),
            relative_volume=compute_relative_volume(asset_snapshot),
        )

    def build_runtime_signal(self, signal_id: str) -> Signal:
        with self._lock:
            signal = self.get_signal_seed(signal_id)
            event = self._events[signal.event_id]
            evidence = self.get_signal_evidence(signal.id)
            price_reaction = self.calculate_signal_price_reaction(signal)
            sources = self.get_event_sources(event.id)
            relation = next(
                (item for item in event.related_assets if item.symbol == signal.asset.symbol),
                event.related_assets[0],
            )

            quality_score = self._source_quality_score(sources)
            corroboration_score = self._corroboration_score(sources)
            coherence_score = self._coherence_score(signal, price_reaction, relation.relationship)
            freshness_score = self._freshness_score(event)
            base_confidence = (
                0.25 * quality_score
                + 0.20 * corroboration_score
                + 0.20 * relation.entity_match_score
                + 0.20 * coherence_score
                + 0.15 * freshness_score
            )
            confidence = apply_confidence_penalties(
                base_confidence,
                has_single_source=len(self._independent_original_publisher_groups(sources)) < 2,
                has_material_contradiction=self._has_material_contradiction(evidence),
                has_incomplete_history=self._has_incomplete_history(signal, price_reaction),
                has_old_fallback=self.get_meta().data_mode == DataMode.FALLBACK,
                has_indirect_relation=relation.relationship == "indirect",
            )
            impact, analysis_status = derive_safe_status(signal.impact, confidence)
            if price_reaction is None or not self._signal_evidence_is_complete(signal, evidence):
                impact = Impact.UNCERTAIN
                analysis_status = AnalysisStatus.INSUFFICIENT_EVIDENCE
                confidence = min(confidence, 0.59)
            return signal.model_copy(
                update={
                    "impact": impact,
                    "confidence": confidence,
                    "analysis_status": analysis_status,
                    "price_reaction": price_reaction,
                }
            )

    def get_asset_id_for_symbol(self, symbol: str) -> str:
        with self._lock:
            return self._assets_by_symbol[symbol].id

    def find_signals_for_event_assets(
        self,
        *,
        event_id: str,
        asset_ids: tuple[str, ...],
    ) -> tuple[Signal, ...]:
        with self._lock:
            return tuple(
                self.build_runtime_signal(signal.id)
                for signal in self._signal_seeds.values()
                if signal.event_id == event_id
                and self.get_asset_id_for_symbol(signal.asset.symbol) in asset_ids
            )

    def _resolve_request_signals(self, request: AnalysisRequest) -> tuple[Signal, ...]:
        valid_asset_symbols = {
            self._assets[asset_id].symbol for asset_id in request.asset_ids if asset_id in self._assets
        }
        return tuple(
            self.build_runtime_signal(signal.id)
            for signal in self._signal_seeds.values()
            if signal.event_id == request.event_id and signal.asset.symbol in valid_asset_symbols
        )

    def _resolve_source_snapshot_ids(self, signals: tuple[Signal, ...]) -> tuple[str, ...]:
        snapshot_ids: set[str] = set()
        for signal in signals:
            event = self._events[signal.event_id]
            snapshot_ids.update(self._articles[article_id].source_snapshot_id for article_id in event.article_ids)
            for evidence in self.get_signal_evidence(signal.id):
                snapshot_ids.update(evidence.market_snapshot_ids)
        return tuple(sorted(snapshot_ids))

    def _build_prioritized_signal(self, signal: Signal) -> PrioritizedSignal:
        priority = "high" if signal.confidence >= 0.75 else "medium" if signal.confidence >= 0.60 else "low"
        reason = (
            f"Impacto {signal.impact.value} para {signal.asset.symbol} con "
            f"confianza {signal.confidence:.2f}."
        )
        with allow_internal_field_names():
            return PrioritizedSignal(
                signal_id=signal.id,
                priority=priority,
                reason=reason,
                suggested_research_actions=signal.suggested_research_actions or ("Revisar evidencia.",),
                review=signal.review,
            )

    def _build_human_review_summary(
        self,
        signals: tuple[Signal, ...] | None = None,
    ) -> HumanReviewSummary:
        selected_signals = signals or tuple(self.build_runtime_signal(signal.id) for signal in self._signal_seeds.values())
        review_statuses = [signal.review.status for signal in selected_signals]
        with allow_internal_field_names():
            return HumanReviewSummary(
                total_signals=len(review_statuses),
                pending_review=sum(status == ReviewStatus.PENDING_REVIEW for status in review_statuses),
                reviewed=sum(status == ReviewStatus.REVIEWED for status in review_statuses),
                escalated=sum(status == ReviewStatus.ESCALATED for status in review_statuses),
                discarded=sum(status == ReviewStatus.DISCARDED for status in review_statuses),
            )

    def _build_review_tasks(
        self,
        signals: tuple[Signal, ...],
        *,
        briefing_id: str,
        created_at: datetime,
        existing_tasks: tuple[ReviewTask, ...] = (),
    ) -> tuple[ReviewTask, ...]:
        tasks_by_key = {(task.signal_id, task.kind): task for task in existing_tasks}
        built_tasks: list[ReviewTask] = []
        for signal in signals:
            review_task = self._build_single_review_task(
                briefing_id=briefing_id,
                signal=signal,
                kind="review",
                created_at=created_at,
                existing=tasks_by_key.get((signal.id, "review")),
            )
            built_tasks.append(review_task)
            existing_escalation = tasks_by_key.get((signal.id, "escalation"))
            if signal.review.status == ReviewStatus.ESCALATED or existing_escalation is not None:
                built_tasks.append(
                    self._build_single_review_task(
                        briefing_id=briefing_id,
                        signal=signal,
                        kind="escalation",
                        created_at=created_at,
                        existing=existing_escalation,
                    )
                )
        return tuple(built_tasks)

    def _build_single_review_task(
        self,
        *,
        briefing_id: str,
        signal: Signal,
        kind: str,
        created_at: datetime,
        existing: ReviewTask | None,
    ) -> ReviewTask:
        task_id = existing.id if existing is not None else f"tsk_{briefing_id}_{signal.id}_{kind}"
        if kind == "review":
            is_resolved = signal.review.status in {ReviewStatus.REVIEWED, ReviewStatus.DISCARDED}
            title = f"Revision humana para {signal.asset.symbol}"
            description = "Confirmar evidencia, supuestos y condiciones de invalidacion."
        else:
            is_resolved = signal.review.status != ReviewStatus.ESCALATED
            title = f"Escalacion para {signal.asset.symbol}"
            description = "Requiere escalacion o validacion senior antes de compartirse."
        resolved_at = signal.review.reviewed_at if is_resolved and signal.review.reviewed_at is not None else None
        task_created_at = existing.created_at if existing is not None else created_at
        if resolved_at is not None and task_created_at > resolved_at:
            task_created_at = resolved_at
        with allow_internal_field_names():
            return ReviewTask(
                id=task_id,
                signal_id=signal.id,
                kind=kind,
                status="resolved" if is_resolved else "open",
                title=title,
                description=description,
                created_at=task_created_at,
                resolved_at=resolved_at,
            )

    def _effective_briefing_status(
        self,
        requested_status: BriefingStatus,
        signals: tuple[Signal, ...],
        review_tasks: tuple[ReviewTask, ...],
    ) -> BriefingStatus:
        if requested_status == BriefingStatus.SHAREABLE:
            self._assert_shareable_signals(signals)
            if any(task.status != "resolved" for task in review_tasks):
                return BriefingStatus.DRAFT
        return requested_status

    def _assert_shareable_signals(self, signals: tuple[Signal, ...]) -> None:
        if any(signal.analysis_status != AnalysisStatus.COMPLETED for signal in signals):
            raise ValueError("Shareable briefings require completed signals only")
        if any(signal.review.status != ReviewStatus.REVIEWED for signal in signals):
            raise ValueError("Shareable briefings require reviewed signals only")

    def _sync_briefings_for_signal(self, signal_id: str, *, updated_at: datetime) -> None:
        for briefing_id, briefing in tuple(self._briefings.items()):
            if signal_id not in {item.signal_id for item in briefing.prioritized_signals}:
                continue
            refreshed = self.get_briefing(briefing_id)
            self._briefings[briefing_id] = refreshed.model_copy(
                update={"updated_at": max(refreshed.updated_at, updated_at)}
            )

    def _signal_evidence_is_complete(self, signal: Signal, evidence: tuple[Evidence, ...]) -> bool:
        evidence_ids = {item.id for item in evidence}
        if not set(signal.evidence_ids) <= evidence_ids:
            return False
        if not set(signal.counter_evidence_ids) <= evidence_ids:
            return False
        if signal.analysis_status == AnalysisStatus.COMPLETED and not signal.evidence_ids:
            return False
        return True

    def _has_material_contradiction(self, evidence: tuple[Evidence, ...]) -> bool:
        return any(not item.supports_signal for item in evidence)

    def _has_incomplete_history(self, signal: Signal, price_reaction: Any | None) -> bool:
        if price_reaction is None:
            return True
        asset = self._assets_by_symbol[signal.asset.symbol]
        if asset.instrument_type.value == "equity" and price_reaction.benchmark_return is None:
            return True
        if asset.instrument_type.value == "equity" and price_reaction.relative_volume is None:
            return True
        return False

    def _source_quality_score(self, sources: tuple[Source, ...]) -> float:
        return sum(SOURCE_TIER_SCORES[source.tier] for source in sources) / len(sources)

    def _corroboration_score(self, sources: tuple[Source, ...]) -> float:
        independent_publishers = len(self._independent_original_publisher_groups(sources))
        if independent_publishers >= 3:
            return 1.0
        if independent_publishers == 2:
            return 0.8
        if independent_publishers == 1:
            return 0.4
        return 0.0

    def _coherence_score(
        self,
        signal: Signal,
        price_reaction: Any | None,
        relationship: str,
    ) -> float:
        if price_reaction is None:
            return 0.35
        if signal.impact == Impact.UNCERTAIN:
            return 0.40
        asset_return = price_reaction.asset_return
        is_aligned = (
            (signal.impact == Impact.POSITIVE and asset_return > 0)
            or (signal.impact == Impact.NEGATIVE and asset_return < 0)
            or (signal.impact == Impact.NEUTRAL and abs(asset_return) <= 0.01)
        )
        base = 0.75 if is_aligned else 0.35
        if price_reaction.abnormal_return is not None and abs(price_reaction.abnormal_return) >= 0.02:
            base += 0.05
        if relationship != "direct":
            base -= 0.05
        return max(0.0, min(1.0, base))

    def _freshness_score(self, event: Event) -> float:
        age_days = (self.fixture_clock - event.event_at).total_seconds() / 86_400
        if age_days <= 1:
            return 0.95
        if age_days <= 2:
            return 0.85
        if age_days <= 7:
            return 0.70
        return 0.40

    def _deduplicate_articles(
        self,
        articles: tuple[Article, ...],
    ) -> tuple[tuple[Article, ...], tuple[str, ...]]:
        seen_keys: set[tuple[str, str, str]] = set()
        deduplicated: list[Article] = []
        duplicate_ids: list[str] = []
        for article in sorted(articles, key=lambda item: (item.published_at, item.id)):
            key = (
                article.provider_article_id,
                self._canonicalize_url(str(article.url)),
                article.content_hash,
            )
            if key in seen_keys:
                duplicate_ids.append(article.id)
                continue
            seen_keys.add(key)
            deduplicated.append(article)
        return tuple(deduplicated), tuple(duplicate_ids)

    def _independent_original_publisher_groups(self, sources: tuple[Source, ...]) -> tuple[str, ...]:
        groups = {
            source.publisher_group_id
            for source in sources
            if source.is_original_publisher and not source.is_aggregator
        }
        return tuple(sorted(groups))

    def _canonicalize_url(self, url: str) -> str:
        parts = urlsplit(url)
        normalized_path = parts.path.rstrip("/") or "/"
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                normalized_path,
                "",
                "",
            )
        )
