"""Offline fixture bundle contract and cross-entity integrity validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated

from pydantic import AwareDatetime, Field, JsonValue, model_validator

from .entities import (
    AgentRun,
    Article,
    Asset,
    Briefing,
    BriefingStatus,
    Claim,
    ContractModel,
    DataMode,
    Event,
    Evidence,
    Identifier,
    MarketSnapshot,
    NonEmptyString,
    ReviewStatus,
    Sha256,
    Signal,
    SignalReview,
    Source,
)


def canonical_json_bytes(value: JsonValue) -> bytes:
    """Return the single canonical JSON representation used by every fixture hash."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_digest(value: JsonValue) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


class FixtureManifest(ContractModel):
    fixture_id: Identifier
    schema_version: NonEmptyString
    fixture_clock: AwareDatetime
    generator_version: NonEmptyString
    fixture_hash: Sha256


class RawSourceSnapshot(ContractModel):
    id: Identifier
    source_id: Identifier
    provider: NonEmptyString
    provider_article_id: NonEmptyString
    captured_at: AwareDatetime
    payload: dict[str, JsonValue]
    content_hash: Sha256

    @model_validator(mode="after")
    def validate_content_hash(self) -> RawSourceSnapshot:
        if self.content_hash != sha256_digest(self.payload):
            raise ValueError("raw source snapshot contentHash does not match payload")
        return self


def market_snapshot_hash_payload(snapshot: MarketSnapshot) -> dict[str, JsonValue]:
    return snapshot.model_dump(
        mode="json",
        by_alias=True,
        exclude={"content_hash"},
    )


def calculation_evidence_hash_payload(
    evidence: Evidence, claim: Claim | None = None
) -> dict[str, JsonValue]:
    payload = evidence.model_dump(
        mode="json",
        by_alias=True,
        exclude={"content_hash"},
    )
    if claim is not None:
        payload["claimValue"] = {
            "numericValue": claim.numeric_value,
            "unit": claim.unit,
        }
    return payload


class FixtureBundle(ContractModel):
    manifest: FixtureManifest
    sources: Annotated[tuple[Source, ...], Field(min_length=1)]
    articles: Annotated[tuple[Article, ...], Field(min_length=1)]
    events: Annotated[tuple[Event, ...], Field(min_length=1)]
    assets: Annotated[tuple[Asset, ...], Field(min_length=1)]
    market_snapshots: Annotated[tuple[MarketSnapshot, ...], Field(min_length=1)]
    claims: Annotated[tuple[Claim, ...], Field(min_length=1)]
    evidence: Annotated[tuple[Evidence, ...], Field(min_length=1)]
    signals: Annotated[tuple[Signal, ...], Field(min_length=1)]
    signal_reviews: tuple[SignalReview, ...]
    briefings: Annotated[tuple[Briefing, ...], Field(min_length=1)]
    agent_runs: Annotated[tuple[AgentRun, ...], Field(min_length=1)]
    raw_source_snapshots: Annotated[tuple[RawSourceSnapshot, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_integrity(self) -> FixtureBundle:
        collections: tuple[tuple[ContractModel, ...], ...] = (
            self.sources,
            self.articles,
            self.events,
            self.assets,
            self.market_snapshots,
            self.claims,
            self.evidence,
            self.signals,
            self.signal_reviews,
            self.agent_runs,
            self.raw_source_snapshots,
        )
        for collection in collections:
            ids = [item.id for item in collection]
            if len(ids) != len(set(ids)):
                raise ValueError("fixture collection IDs must be unique")
        all_ids = [item.id for collection in collections for item in collection]
        all_ids.extend(item.briefing_id for item in self.briefings)
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("fixture IDs must be globally unique")

        sources = {item.id: item for item in self.sources}
        articles = {item.id: item for item in self.articles}
        events = {item.id: item for item in self.events}
        assets = {item.id: item for item in self.assets}
        assets_by_symbol = {item.symbol: item for item in self.assets}
        if len(assets_by_symbol) != len(self.assets):
            raise ValueError("Asset.symbol must be unique")
        snapshots = {item.id: item for item in self.market_snapshots}
        claims = {item.id: item for item in self.claims}
        evidence = {item.id: item for item in self.evidence}
        signals = {item.id: item for item in self.signals}
        reviews_by_signal: dict[str, list[SignalReview]] = {}
        raw_snapshots = {item.id: item for item in self.raw_source_snapshots}

        domain_groups: dict[str, str] = {}
        for source in self.sources:
            previous_group = domain_groups.setdefault(source.domain, source.publisher_group_id)
            if previous_group != source.publisher_group_id:
                raise ValueError(
                    "one publisher domain cannot represent multiple independent groups"
                )

        original_groups = {
            source.publisher_group_id
            for source in self.sources
            if source.is_original_publisher and not source.is_aggregator
        }
        if len(original_groups) < 2:
            raise ValueError("fixtures require at least two independent original publishers")

        for article in self.articles:
            source = sources.get(article.source_id)
            raw_snapshot = raw_snapshots.get(article.source_snapshot_id)
            if source is None or raw_snapshot is None:
                raise ValueError("article references an unknown source or raw snapshot")
            if raw_snapshot.source_id != source.id:
                raise ValueError("raw snapshot source does not match Article.sourceId")
            if raw_snapshot.provider != article.provider:
                raise ValueError("ingestion provider must match between article and raw snapshot")
            if raw_snapshot.provider_article_id != article.provider_article_id:
                raise ValueError("provider article ID must match the raw snapshot")
            if raw_snapshot.captured_at != article.retrieved_at:
                raise ValueError("raw snapshot capturedAt must match Article.retrievedAt")
            if raw_snapshot.content_hash != article.content_hash:
                raise ValueError("article contentHash must resolve to its raw source snapshot")

        for event in self.events:
            event_articles = []
            for article_id in event.article_ids:
                article = articles.get(article_id)
                if article is None:
                    raise ValueError("event references an unknown article")
                event_articles.append(article)
            for relation in event.related_assets:
                asset = assets.get(relation.asset_id)
                if asset is None or asset.symbol != relation.symbol:
                    raise ValueError("event asset relation is unresolved or inconsistent")
            event_sources = [sources[article.source_id] for article in event_articles]
            publisher_groups = {
                source.publisher_group_id
                for source in event_sources
                if source.is_original_publisher and not source.is_aggregator
            }
            if len(publisher_groups) < 2:
                raise ValueError("each fixture event requires two independent publishers")
            if any(article.retrieved_at > event.retrieved_at for article in event_articles):
                raise ValueError("event cannot be retrieved before its articles")

        for snapshot in self.market_snapshots:
            if snapshot.asset_id not in assets:
                raise ValueError("market snapshot references an unknown asset")
            if snapshot.benchmark_asset_id and snapshot.benchmark_asset_id not in assets:
                raise ValueError("market snapshot references an unknown benchmark")
            if snapshot.content_hash != sha256_digest(market_snapshot_hash_payload(snapshot)):
                raise ValueError("market snapshot contentHash is invalid")

        for item in self.evidence:
            claim = claims.get(item.claim_id)
            signal = signals.get(item.signal_id)
            if claim is None or signal is None:
                raise ValueError("evidence references an unknown claim or signal")
            if claim.signal_id != signal.id or claim.claim != item.claim:
                raise ValueError("evidence does not match its claim/signal")
            if item.evidence_type == "source":
                article = articles.get(item.article_id or "")
                if article is None or article.source_id != item.source_id:
                    raise ValueError("source evidence does not resolve Article -> Source")
                if item.source_snapshot_id != article.source_snapshot_id:
                    raise ValueError("source evidence does not resolve the raw snapshot")
                if item.content_hash != article.content_hash:
                    raise ValueError("source evidence contentHash does not match Article")
                if (
                    item.source_url != article.url
                    or item.published_at != article.published_at
                    or item.retrieved_at != article.retrieved_at
                    or item.data_as_of != article.data_as_of
                ):
                    raise ValueError("source evidence provenance must match Article exactly")
            else:
                resolved = [snapshots.get(snapshot_id) for snapshot_id in item.market_snapshot_ids]
                if any(snapshot is None for snapshot in resolved):
                    raise ValueError("evidence references an unknown market snapshot")
                if item.evidence_type in {"market_data", "context"} and len(resolved) == 1:
                    expected_hash = resolved[0].content_hash
                else:
                    expected_hash = sha256_digest(
                        calculation_evidence_hash_payload(item, claim)
                    )
                if item.content_hash != expected_hash:
                    raise ValueError("market/calculation evidence contentHash is invalid")

        for claim in self.claims:
            signal = signals.get(claim.signal_id)
            if claim.event_id not in events or signal is None:
                raise ValueError("claim references an unknown event or signal")
            if signal.event_id != claim.event_id:
                raise ValueError("Claim.eventId must match its Signal.eventId")
            referenced = (*claim.evidence_ids, *claim.counter_evidence_ids)
            if any(evidence_id not in evidence for evidence_id in referenced):
                raise ValueError("claim references unknown evidence")
            for evidence_id in claim.evidence_ids:
                evidence_item = evidence[evidence_id]
                if (
                    evidence_item.claim_id != claim.id
                    or evidence_item.signal_id != claim.signal_id
                    or not evidence_item.supports_signal
                ):
                    raise ValueError("claim evidenceIds must contain supporting evidence")
            for evidence_id in claim.counter_evidence_ids:
                evidence_item = evidence[evidence_id]
                if (
                    evidence_item.claim_id != claim.id
                    or evidence_item.signal_id != claim.signal_id
                    or evidence_item.supports_signal
                ):
                    raise ValueError("claim counterEvidenceIds must contain counter evidence")

        for signal in self.signals:
            event = events.get(signal.event_id)
            asset = assets_by_symbol.get(signal.asset.symbol)
            if event is None or asset is None:
                raise ValueError("signal references an unknown event or asset")
            if (
                signal.asset.name != asset.name
                or signal.asset.instrument_type != asset.instrument_type
            ):
                raise ValueError("embedded Signal.asset does not match the asset catalog")
            event_asset_ids = {relation.asset_id for relation in event.related_assets}
            if asset.id not in event_asset_ids:
                raise ValueError("signal asset is not related to its event")
            if any(evidence_id not in evidence for evidence_id in signal.evidence_ids):
                raise ValueError("signal references unknown supporting evidence")
            if any(evidence_id not in evidence for evidence_id in signal.counter_evidence_ids):
                raise ValueError("signal references unknown counter evidence")
            for evidence_id in signal.evidence_ids:
                if evidence[evidence_id].signal_id != signal.id or not evidence[
                    evidence_id
                ].supports_signal:
                    raise ValueError("signal supporting evidence is inconsistent")
            for evidence_id in signal.counter_evidence_ids:
                if evidence[evidence_id].signal_id != signal.id or evidence[
                    evidence_id
                ].supports_signal:
                    raise ValueError("signal counter evidence is inconsistent")

        for review in self.signal_reviews:
            if review.signal_id not in signals:
                raise ValueError("review references an unknown signal")
            reviews_by_signal.setdefault(review.signal_id, []).append(review)
        for signal in self.signals:
            history = sorted(
                reviews_by_signal.get(signal.id, []), key=lambda item: item.created_at
            )
            if not history:
                if signal.review.status != ReviewStatus.PENDING_REVIEW:
                    raise ValueError("a terminal signal review requires immutable history")
                continue
            expected_previous_status = ReviewStatus.PENDING_REVIEW
            previous_created_at = None
            for review in history:
                if review.previous_status != expected_previous_status:
                    raise ValueError("signal review history has a broken status chain")
                if previous_created_at is not None and review.created_at <= previous_created_at:
                    raise ValueError("signal review history timestamps must increase strictly")
                expected_previous_status = review.status
                previous_created_at = review.created_at
            latest = history[-1]
            if (
                signal.review.status != latest.status
                or signal.review.justification != latest.justification
                or signal.review.reviewed_by != latest.reviewed_by
                or signal.review.reviewed_at != latest.reviewed_at
            ):
                raise ValueError("Signal.review must match its latest immutable review")

        review_counts = {
            ReviewStatus.PENDING_REVIEW: 0,
            ReviewStatus.REVIEWED: 0,
            ReviewStatus.ESCALATED: 0,
            ReviewStatus.DISCARDED: 0,
        }
        for signal in self.signals:
            review_counts[signal.review.status] += 1

        for briefing in self.briefings:
            summary = briefing.human_review_summary
            expected_summary = (
                len(self.signals),
                review_counts[ReviewStatus.PENDING_REVIEW],
                review_counts[ReviewStatus.REVIEWED],
                review_counts[ReviewStatus.ESCALATED],
                review_counts[ReviewStatus.DISCARDED],
            )
            actual_summary = (
                summary.total_signals,
                summary.pending_review,
                summary.reviewed,
                summary.escalated,
                summary.discarded,
            )
            if actual_summary != expected_summary:
                raise ValueError("fixture briefing review summary must match all demo signals")
            for item in briefing.prioritized_signals:
                signal = signals.get(item.signal_id)
                if signal is None or item.review != signal.review:
                    raise ValueError("briefing signal/review is unresolved or inconsistent")
                if item.suggested_research_actions != signal.suggested_research_actions:
                    raise ValueError("briefing actions must come from the signal contract")
                if briefing.status == BriefingStatus.SHAREABLE and (
                    signal.analysis_status.value != "completed"
                    or signal.review.status != ReviewStatus.REVIEWED
                ):
                    raise ValueError("shareable briefing contains an ineligible signal")

        valid_source_snapshot_ids = set(raw_snapshots) | set(snapshots)
        for run in self.agent_runs:
            if any(
                snapshot_id not in valid_source_snapshot_ids
                for snapshot_id in run.source_snapshot_ids
            ):
                raise ValueError("agent run references an unknown source snapshot")

        expected_assets = {"AAPL", "SPY", "BTC-USD", "WTI"}
        if not expected_assets.issubset(assets_by_symbol):
            raise ValueError("fixtures must cover AAPL/SPY, BTC and WTI")
        snapshots_by_asset: dict[str, list[MarketSnapshot]] = {}
        for snapshot in self.market_snapshots:
            snapshots_by_asset.setdefault(snapshot.asset_id, []).append(snapshot)
        for symbol in expected_assets:
            if assets_by_symbol[symbol].id not in snapshots_by_asset:
                raise ValueError(f"fixture asset {symbol} requires a market snapshot")

        aapl_asset = assets_by_symbol["AAPL"]
        spy_asset = assets_by_symbol["SPY"]
        aapl_snapshots = snapshots_by_asset[aapl_asset.id]
        if aapl_asset.benchmark_asset_id != spy_asset.id or not any(
            snapshot.benchmark_asset_id == spy_asset.id
            and len(snapshot.observations) >= 21
            and all(point.volume is not None for point in snapshot.observations[-21:])
            for snapshot in aapl_snapshots
        ):
            raise ValueError("AAPL fixture requires SPY plus 20-session volume context")

        btc_asset = assets_by_symbol["BTC-USD"]
        if not any(
            len(snapshot.observations) >= 31
            and (snapshot.end_at - snapshot.start_at).total_seconds() >= 30 * 86_400
            for snapshot in snapshots_by_asset[btc_asset.id]
        ):
            raise ValueError("BTC fixture requires a 30-day baseline and 24-hour reaction")

        wti_asset = assets_by_symbol["WTI"]
        if not any(
            (snapshot.end_at - snapshot.start_at).total_seconds() >= 30 * 86_400
            and snapshot.missing_value_policy == "skip_non_trading_days"
            for snapshot in snapshots_by_asset[wti_asset.id]
        ):
            raise ValueError("WTI fixture requires 30-day contextual coverage")
        if any(item.data_mode != DataMode.FIXTURE for item in self.articles):
            raise ValueError("all Phase 0 article fixtures must use fixture mode")
        if any(item.data_mode != DataMode.FIXTURE for item in self.events):
            raise ValueError("all Phase 0 event fixtures must use fixture mode")
        if any(item.data_mode != DataMode.FIXTURE for item in self.market_snapshots):
            raise ValueError("all Phase 0 market fixtures must use fixture mode")
        if any(
            item.freshness.evaluated_at != self.manifest.fixture_clock
            for item in (*self.articles, *self.events, *self.market_snapshots)
        ):
            raise ValueError("fixture freshness must use the manifest fixtureClock")

        timestamps = [
            *(item.published_at for item in self.articles),
            *(item.retrieved_at for item in self.articles),
            *(item.data_as_of for item in self.articles),
            *(item.event_at for item in self.events),
            *(item.created_at for item in self.events),
            *(item.updated_at for item in self.events),
            *(item.retrieved_at for item in self.events),
            *(item.data_as_of for item in self.events),
            *(item.start_at for item in self.market_snapshots),
            *(item.end_at for item in self.market_snapshots),
            *(item.retrieved_at for item in self.market_snapshots),
            *(item.data_as_of for item in self.market_snapshots),
            *(
                point.timestamp
                for item in self.market_snapshots
                for point in item.observations
            ),
            *(item.created_at for item in self.claims),
            *(item.retrieved_at for item in self.evidence),
            *(item.data_as_of for item in self.evidence),
            *(item.created_at for item in self.signals),
            *(item.updated_at for item in self.signals),
            *(item.reviewed_at for item in self.signal_reviews),
            *(item.created_at for item in self.signal_reviews),
            *(item.created_at for item in self.briefings),
            *(item.updated_at for item in self.briefings),
            *(item.started_at for item in self.agent_runs),
            *(item.captured_at for item in self.raw_source_snapshots),
        ]
        timestamps.extend(
            item.published_at for item in self.evidence if item.published_at is not None
        )
        timestamps.extend(
            item.finished_at for item in self.agent_runs if item.finished_at is not None
        )
        timestamps.extend(
            item.review.reviewed_at
            for item in self.signals
            if item.review.reviewed_at is not None
        )
        if any(timestamp > self.manifest.fixture_clock for timestamp in timestamps):
            raise ValueError("fixture timestamps must not exceed fixtureClock")
        if self.manifest.fixture_hash != build_fixture_hash(self):
            raise ValueError("fixture manifest hash does not match the normalized bundle")
        return self

def build_fixture_hash(bundle: FixtureBundle) -> str:
    payload = bundle.model_dump(mode="json", by_alias=True)
    payload["manifest"]["fixtureHash"] = None
    return sha256_digest(payload)


def load_fixture_bundle(path: Path) -> FixtureBundle:
    """Load a bundle from disk without consulting providers, clocks or environment secrets."""

    return FixtureBundle.model_validate_json(path.read_text(encoding="utf-8"))


__all__ = [
    "FixtureBundle",
    "FixtureManifest",
    "RawSourceSnapshot",
    "build_fixture_hash",
    "calculation_evidence_hash_payload",
    "canonical_json_bytes",
    "load_fixture_bundle",
    "market_snapshot_hash_payload",
    "sha256_digest",
]
