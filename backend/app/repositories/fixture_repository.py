"""Fixture-backed repository with in-memory overlays for mutable flows."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import Any

from app.calculations.returns import build_price_reaction, compute_asset_return, compute_relative_volume
from app.contracts.api import AgentRunStep, AnalysisRequest, BriefingRequest, ReviewRequest, Watchlist
from app.contracts.entities import (
    DISCLAIMER,
    AgentRun,
    AnalysisStatus,
    Briefing,
    BriefingStatus,
    DataMode,
    DataProvenance,
    Event,
    Evidence,
    Freshness,
    HumanReviewSummary,
    PrioritizedSignal,
    ReviewStatus,
    ReviewSummary,
    Reviewer,
    Signal,
    SignalReview,
    WatchlistRef,
    allow_internal_field_names,
)
from app.contracts.fixtures import FixtureBundle, canonical_json_bytes, sha256_digest
from app.providers.fixture_provider import FixtureProvider
from app.repositories.base import BackendRepository


FIXTURE_WARNINGS: tuple[str, ...] = ("FIXTURE_DATA", "NOT_REAL_TIME")
PROMPT_VERSION = "backend-f1-f5-v1"
REVIEWER = {"id": "usr_analista_demo", "name": "Analista Demo"}


class FixtureRepository(BackendRepository):
    """Read the canonical fixture bundle and keep mutable state in memory."""

    def __init__(self, provider: FixtureProvider) -> None:
        self._provider = provider
        self._bundle = provider.load_bundle()
        self._sources = {item.id: item for item in self._bundle.sources}
        self._articles = {item.id: item for item in self._bundle.articles}
        self._events = {item.id: item for item in self._bundle.events}
        self._assets = {item.id: item for item in self._bundle.assets}
        self._assets_by_symbol = {item.symbol: item for item in self._bundle.assets}
        self._snapshots = {item.id: item for item in self._bundle.market_snapshots}
        self._claims = {item.id: item for item in self._bundle.claims}
        self._evidence = {item.id: item for item in self._bundle.evidence}
        self._signals = {item.id: item for item in self._bundle.signals}
        self._reviews_by_signal: dict[str, list[SignalReview]] = defaultdict(list)
        for review in self._bundle.signal_reviews:
            self._reviews_by_signal[review.signal_id].append(review)
        self._briefings = {item.briefing_id: item for item in self._bundle.briefings}
        self._runs = {item.id: item for item in self._bundle.agent_runs}
        self._run_steps: dict[str, list[AgentRunStep]] = defaultdict(list)
        self._analysis_idempotency: dict[str, tuple[str, bytes]] = {}
        self._review_idempotency: dict[str, tuple[str, bytes]] = {}
        self._briefing_idempotency: dict[str, tuple[str, bytes]] = {}

    @property
    def fixture_clock(self) -> datetime:
        return self._bundle.manifest.fixture_clock

    def get_meta(self) -> DataProvenance:
        clock = self._bundle.manifest.fixture_clock
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
        result: list[Signal] = []
        for signal in self._signals.values():
            if instrument_type and signal.asset.instrument_type.value != instrument_type:
                continue
            if asset and signal.asset.symbol != asset:
                continue
            if published_after:
                event = self._events[signal.event_id]
                if event.event_at.isoformat().replace("+00:00", "Z") <= published_after:
                    continue
            result.append(signal)
        return tuple(sorted(result, key=lambda signal: signal.id))

    def get_signal(self, signal_id: str) -> Signal:
        signal = self._signals.get(signal_id)
        if signal is None:
            raise KeyError(signal_id)
        return signal

    def get_signal_evidence(self, signal_id: str) -> tuple[Evidence, ...]:
        if signal_id not in self._signals:
            raise KeyError(signal_id)
        result = tuple(item for item in self._bundle.evidence if item.signal_id == signal_id)
        return tuple(sorted(result, key=lambda item: item.id))

    def list_signal_reviews(self, signal_id: str) -> tuple[SignalReview, ...]:
        if signal_id not in self._signals:
            raise KeyError(signal_id)
        return tuple(sorted(self._reviews_by_signal.get(signal_id, []), key=lambda item: item.created_at))

    def create_signal_review(
        self,
        signal_id: str,
        request: ReviewRequest,
        *,
        idempotency_key: str,
    ) -> tuple[SignalReview, ...]:
        signal = self.get_signal(signal_id)
        payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
        previous_result = self._review_idempotency.get(idempotency_key)
        if previous_result is not None:
            previous_signal_id, previous_payload = previous_result
            if previous_signal_id != signal_id or previous_payload != payload:
                raise ValueError("Idempotency-Key already used with a different review payload")
            return self.list_signal_reviews(signal_id)

        if signal.review.status == ReviewStatus(request.status):
            raise ValueError("Signal is already in the requested review status")

        review_index = len(self._reviews_by_signal.get(signal_id, [])) + 1
        reviewed_at = self.fixture_clock + timedelta(minutes=review_index)
        created_at = reviewed_at + timedelta(seconds=30)
        review_status = ReviewStatus(request.status)

        with allow_internal_field_names():
            reviewer = Reviewer(**REVIEWER)
            review = SignalReview(
                id=f"rev_{signal_id}_{review_index:03d}",
                signal_id=signal_id,
                previous_status=signal.review.status,
                status=review_status,
                justification=request.justification,
                reviewed_by=reviewer,
                reviewed_at=reviewed_at,
                created_at=created_at,
            )
            review_summary = ReviewSummary(
                status=review_status,
                justification=request.justification,
                reviewed_by=reviewer,
                reviewed_at=reviewed_at,
            )

        self._reviews_by_signal[signal_id].append(review)
        self._signals[signal_id] = signal.model_copy(
            update={
                "review": review_summary,
                "updated_at": created_at,
            }
        )
        self._review_idempotency[idempotency_key] = (signal_id, payload)
        return self.list_signal_reviews(signal_id)

    def create_briefing(
        self,
        request: BriefingRequest,
        *,
        idempotency_key: str,
        executive_summary: str,
    ) -> Briefing:
        payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
        previous_result = self._briefing_idempotency.get(idempotency_key)
        if previous_result is not None:
            briefing_id, previous_payload = previous_result
            if previous_payload != payload:
                raise ValueError("Idempotency-Key already used with a different briefing payload")
            return self.get_briefing(briefing_id)

        signals = tuple(self.get_signal(signal_id) for signal_id in request.signal_ids)
        if request.status == BriefingStatus.SHAREABLE:
            if any(signal.analysis_status != AnalysisStatus.COMPLETED for signal in signals):
                raise ValueError("Shareable briefings require completed signals only")
            if any(signal.review.status != ReviewStatus.REVIEWED for signal in signals):
                raise ValueError("Shareable briefings require reviewed signals only")

        created_at = self.fixture_clock + timedelta(
            minutes=len(self._briefings) + 10
        )
        briefing_id = f"brf_runtime_{len(self._briefings) + 1:03d}"
        review_summary = self._build_human_review_summary()
        prioritized_signals = tuple(
            self._build_prioritized_signal(signal) for signal in signals
        )
        with allow_internal_field_names():
            briefing = Briefing(
                briefing_id=briefing_id,
                status=request.status,
                watchlist=WatchlistRef(id="watchlist_demo_global", name="Demo Global"),
                executive_summary=executive_summary,
                prioritized_signals=prioritized_signals,
                human_review_summary=review_summary,
                requires_human_review=True,
                disclaimer=DISCLAIMER,
                created_at=created_at,
                updated_at=created_at,
            )
        self._briefings[briefing.briefing_id] = briefing
        self._briefing_idempotency[idempotency_key] = (briefing.briefing_id, payload)
        return briefing

    def get_briefing(self, briefing_id: str) -> Briefing:
        briefing = self._briefings.get(briefing_id)
        if briefing is None:
            raise KeyError(briefing_id)
        return briefing

    def create_analysis_run(
        self,
        request: AnalysisRequest,
        *,
        idempotency_key: str,
        model_name: str,
        prompt_version: str,
    ) -> AgentRun:
        payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
        previous_result = self._analysis_idempotency.get(idempotency_key)
        if previous_result is not None:
            run_id, previous_payload = previous_result
            if previous_payload != payload:
                raise ValueError("Idempotency-Key already used with a different analysis payload")
            return self.get_analysis_run(run_id)

        matched_signals = self._resolve_request_signals(request)
        if not matched_signals:
            raise KeyError("No fixture signal matches the requested event and assets")

        started_at = self.fixture_clock + timedelta(minutes=len(self._runs) + 1)
        finished_at = started_at + timedelta(seconds=10)
        statuses = {signal.analysis_status for signal in matched_signals}
        run_status = (
            AnalysisStatus.INSUFFICIENT_EVIDENCE
            if statuses == {AnalysisStatus.INSUFFICIENT_EVIDENCE}
            else AnalysisStatus.COMPLETED
        )
        run_id = f"run_runtime_{len(self._runs) + 1:03d}"
        with allow_internal_field_names():
            run = AgentRun(
                id=run_id,
                organization_id="org_demo",
                conversation_id=None,
                current_node="pending_review",
                status=run_status,
                model_name=model_name,
                prompt_version=prompt_version,
                input_hash=sha256_digest(request.model_dump(mode="json", by_alias=True)),
                source_snapshot_ids=self._resolve_source_snapshot_ids(matched_signals),
                started_at=started_at,
                finished_at=finished_at,
                error_code=None,
                retry_count=0,
            )
        self._runs[run.id] = run
        self._run_steps[run.id] = []
        self._analysis_idempotency[idempotency_key] = (run.id, payload)
        return run

    def get_analysis_run(self, run_id: str) -> AgentRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def set_run_steps(self, run_id: str, steps: tuple[AgentRunStep, ...]) -> None:
        if run_id not in self._runs:
            raise KeyError(run_id)
        self._run_steps[run_id] = list(steps)

    def get_run_steps(self, run_id: str) -> tuple[AgentRunStep, ...]:
        if run_id not in self._runs:
            raise KeyError(run_id)
        return tuple(self._run_steps.get(run_id, []))

    def get_event_articles(self, event_id: str) -> tuple[Any, ...]:
        event = self._events[event_id]
        return tuple(self._articles[article_id] for article_id in event.article_ids)

    def get_event_sources(self, event_id: str) -> tuple[Any, ...]:
        articles = self.get_event_articles(event_id)
        source_ids = {article.source_id for article in articles}
        return tuple(self._sources[source_id] for source_id in sorted(source_ids))

    def get_event_market_snapshots(self, event: Event) -> tuple[Any, ...]:
        relation_asset_ids = {relation.asset_id for relation in event.related_assets}
        return tuple(
            snapshot
            for snapshot in self._bundle.market_snapshots
            if snapshot.asset_id in relation_asset_ids
        )

    def get_event_asset_relations(self, event_id: str) -> tuple[dict[str, str], ...]:
        event = self._events[event_id]
        return tuple(
            {
                "assetId": relation.asset_id,
                "symbol": relation.symbol,
                "relationship": relation.relationship,
                "reason": relation.reason,
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
        benchmark_return = None
        if primary_asset.benchmark_asset_id is not None:
            benchmark_snapshot = next(
                (
                    snapshot
                    for snapshot in self._bundle.market_snapshots
                    if snapshot.asset_id == primary_asset.benchmark_asset_id
                ),
                None,
            )
            if benchmark_snapshot is not None:
                benchmark_return = compute_asset_return(benchmark_snapshot)
        return build_price_reaction(
            asset_return=compute_asset_return(asset_snapshot),
            benchmark_return=benchmark_return,
            relative_volume=compute_relative_volume(asset_snapshot),
        )

    def get_asset_id_for_symbol(self, symbol: str) -> str:
        return self._assets_by_symbol[symbol].id

    def find_signals_for_event_assets(
        self,
        *,
        event_id: str,
        asset_ids: tuple[str, ...],
    ) -> tuple[Signal, ...]:
        return tuple(
            signal
            for signal in self.list_signals()
            if signal.event_id == event_id and self.get_asset_id_for_symbol(signal.asset.symbol) in asset_ids
        )

    def _resolve_request_signals(self, request: AnalysisRequest) -> tuple[Signal, ...]:
        valid_asset_symbols = {
            self._assets[asset_id].symbol for asset_id in request.asset_ids if asset_id in self._assets
        }
        return tuple(
            signal
            for signal in self._signals.values()
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

    def _build_human_review_summary(self) -> HumanReviewSummary:
        review_statuses = [signal.review.status for signal in self._signals.values()]
        with allow_internal_field_names():
            return HumanReviewSummary(
                total_signals=len(review_statuses),
                pending_review=sum(status == ReviewStatus.PENDING_REVIEW for status in review_statuses),
                reviewed=sum(status == ReviewStatus.REVIEWED for status in review_statuses),
                escalated=sum(status == ReviewStatus.ESCALATED for status in review_statuses),
                discarded=sum(status == ReviewStatus.DISCARDED for status in review_statuses),
            )
