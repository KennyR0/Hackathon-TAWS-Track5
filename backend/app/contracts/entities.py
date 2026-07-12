"""Strict Pydantic entities shared by every NexoMercado consumer."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

DISCLAIMER = (
    "Esta señal es informativa, no constituye asesoría financiera personalizada "
    "ni garantiza resultados."
)
DisclaimerText = Literal[
    "Esta señal es informativa, no constituye asesoría financiera personalizada "
    "ni garantiza resultados."
]

Identifier = Annotated[
    StrictStr,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=96,
        pattern=r"^[a-z][a-z0-9_:-]*$",
    ),
]
NonEmptyString = Annotated[StrictStr, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[StrictStr, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
LanguageCode = Annotated[
    StrictStr,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=15,
        pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$",
    ),
]
AssetSymbol = Annotated[
    StrictStr,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=24,
        pattern=r"^[A-Z0-9][A-Z0-9./-]*$",
    ),
]
CurrencyCode = Annotated[StrictStr, StringConstraints(pattern=r"^[A-Z]{3}$")]
UnitInterval = Annotated[StrictFloat, Field(ge=0.0, le=1.0)]
NonNegativeFloat = Annotated[StrictFloat, Field(ge=0.0)]
NonNegativeInt = Annotated[StrictInt, Field(ge=0)]

_ALLOW_INTERNAL_FIELD_NAMES: ContextVar[bool] = ContextVar(
    "allow_internal_field_names", default=False
)


@contextmanager
def allow_internal_field_names() -> Iterator[None]:
    """Permit snake_case only while trusted code constructs Python model objects."""

    token = _ALLOW_INTERNAL_FIELD_NAMES.set(True)
    try:
        yield
    finally:
        _ALLOW_INTERNAL_FIELD_NAMES.reset(token)


class ContractModel(BaseModel):
    """Base configuration that rejects undeclared consumer fields."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        allow_inf_nan=False,
        extra="forbid",
        frozen=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
        strict=False,
        validate_default=True,
        validate_by_alias=True,
        validate_by_name=False,
    )

    def __init__(self, **data: object) -> None:
        """Allow explicit Python field names without accepting them on the wire."""

        if not _ALLOW_INTERNAL_FIELD_NAMES.get():
            super().__init__(**data)
            return
        canonical_data: dict[str, object] = {}
        for key, value in data.items():
            field = type(self).model_fields.get(key)
            canonical_key = field.alias if field is not None and field.alias else key
            if canonical_key in canonical_data:
                raise ValueError(f"duplicate field supplied for {canonical_key}")
            canonical_data[canonical_key] = value
        super().__init__(**canonical_data)


class Impact(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNCERTAIN = "uncertain"


class AnalysisStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    REVIEWED = "reviewed"
    ESCALATED = "escalated"
    DISCARDED = "discarded"


class BriefingStatus(StrEnum):
    DRAFT = "draft"
    SHAREABLE = "shareable"


class DataMode(StrEnum):
    FIXTURE = "fixture"
    LIVE = "live"
    FALLBACK = "fallback"


class InstrumentType(StrEnum):
    EQUITY = "equity"
    ETF = "etf"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    MACRO = "macro"
    CREDIT = "credit"
    OTHER = "other"


class SourceTier(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Freshness(ContractModel):
    evaluated_at: AwareDatetime
    stale_after_seconds: Annotated[StrictInt, Field(gt=0)]
    is_stale: StrictBool


class DataProvenance(ContractModel):
    data_mode: DataMode
    provider: NonEmptyString
    retrieved_at: AwareDatetime
    data_as_of: AwareDatetime
    freshness: Freshness
    warnings: tuple[NonEmptyString, ...]

    @model_validator(mode="after")
    def validate_provenance(self) -> DataProvenance:
        if self.data_as_of > self.retrieved_at:
            raise ValueError("dataAsOf must not be later than retrievedAt")
        if self.retrieved_at > self.freshness.evaluated_at:
            raise ValueError("retrievedAt must not be later than freshness.evaluatedAt")
        age_seconds = (self.freshness.evaluated_at - self.data_as_of).total_seconds()
        expected_is_stale = age_seconds > self.freshness.stale_after_seconds
        if self.freshness.is_stale != expected_is_stale:
            raise ValueError("freshness.isStale must be derived from dataAsOf and evaluatedAt")
        if self.data_mode in {DataMode.FIXTURE, DataMode.FALLBACK} and not self.warnings:
            raise ValueError("fixture and fallback data must declare freshness warnings")
        return self


class Source(ContractModel):
    id: Identifier
    name: NonEmptyString
    domain: Annotated[StrictStr, StringConstraints(pattern=r"^[a-z0-9.-]+\.[a-z]{2,}$")]
    tier: SourceTier
    publisher_group_id: Identifier
    is_original_publisher: StrictBool
    is_aggregator: StrictBool
    fixture_only: StrictBool
    homepage_url: HttpUrl
    country_code: Annotated[StrictStr, StringConstraints(pattern=r"^[A-Z]{2}$")]
    language: LanguageCode

    @model_validator(mode="after")
    def validate_publisher_role(self) -> Source:
        if self.is_original_publisher and self.is_aggregator:
            raise ValueError("an original publisher cannot also be an aggregator")
        return self


class Article(DataProvenance):
    id: Identifier
    source_id: Identifier
    provider_article_id: NonEmptyString
    headline: NonEmptyString
    summary: NonEmptyString
    published_at: AwareDatetime
    url: HttpUrl
    language: LanguageCode
    source_snapshot_id: Identifier
    content_hash: Sha256
    is_synthetic: StrictBool

    @model_validator(mode="after")
    def validate_article_timeline(self) -> Article:
        if self.published_at > self.data_as_of:
            raise ValueError("publishedAt must not be later than dataAsOf")
        return self


class Asset(ContractModel):
    id: Identifier
    symbol: AssetSymbol
    name: NonEmptyString
    instrument_type: InstrumentType
    currency: CurrencyCode
    exchange: NonEmptyString | None = None
    benchmark_asset_id: Identifier | None = None
    series_id: NonEmptyString | None = None


class AssetRef(ContractModel):
    symbol: AssetSymbol
    name: NonEmptyString
    instrument_type: InstrumentType


class AssetRelation(ContractModel):
    asset_id: Identifier
    symbol: AssetSymbol
    relationship: Literal[
        "direct",
        "sector",
        "competitor",
        "supply_chain",
        "macro",
        "commodity",
        "credit",
        "indirect",
    ]
    reason: NonEmptyString
    entity_match_score: UnitInterval


class Event(DataProvenance):
    id: Identifier
    title: NonEmptyString
    summary: NonEmptyString
    event_at: AwareDatetime
    article_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    related_assets: Annotated[tuple[AssetRelation, ...], Field(min_length=1)]
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @field_validator("article_ids")
    @classmethod
    def validate_unique_article_ids(cls, value: tuple[Identifier, ...]) -> tuple[Identifier, ...]:
        if len(value) != len(set(value)):
            raise ValueError("articleIds must be unique")
        return value

    @field_validator("related_assets")
    @classmethod
    def validate_unique_related_assets(
        cls, value: tuple[AssetRelation, ...]
    ) -> tuple[AssetRelation, ...]:
        asset_ids = [relation.asset_id for relation in value]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("relatedAssets must not repeat an assetId")
        return value

    @model_validator(mode="after")
    def validate_event_timeline(self) -> Event:
        if self.event_at > self.data_as_of:
            raise ValueError("eventAt must not be later than dataAsOf")
        if self.created_at > self.updated_at:
            raise ValueError("createdAt must not be later than updatedAt")
        return self


class MarketPoint(ContractModel):
    timestamp: AwareDatetime
    close: StrictFloat
    volume: NonNegativeFloat | None = None
    open: StrictFloat | None = None
    high: StrictFloat | None = None
    low: StrictFloat | None = None

    @model_validator(mode="after")
    def validate_ohlc(self) -> MarketPoint:
        optional_ohlc = (self.open, self.high, self.low)
        if any(value is not None for value in optional_ohlc) and not all(
            value is not None for value in optional_ohlc
        ):
            raise ValueError("open, high and low must be supplied together")
        if self.open is None or self.high is None or self.low is None:
            return self
        if self.low > self.high:
            raise ValueError("low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise ValueError("open must be inside the low/high range")
        if not self.low <= self.close <= self.high:
            raise ValueError("close must be inside the low/high range")
        return self


class MarketSnapshot(DataProvenance):
    id: Identifier
    asset_id: Identifier
    benchmark_asset_id: Identifier | None = None
    series_id: NonEmptyString | None = None
    interval: Literal["1h", "1d"]
    currency: CurrencyCode
    timezone: NonEmptyString
    start_at: AwareDatetime
    end_at: AwareDatetime
    source_url: HttpUrl
    observations: Annotated[tuple[MarketPoint, ...], Field(min_length=2)]
    missing_value_policy: Literal["none", "skip_non_trading_days"]
    content_hash: Sha256

    @model_validator(mode="after")
    def validate_market_timeline(self) -> MarketSnapshot:
        timestamps = [point.timestamp for point in self.observations]
        if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
            raise ValueError("observations must have unique, ascending timestamps")
        if self.start_at != timestamps[0] or self.end_at != timestamps[-1]:
            raise ValueError("startAt/endAt must match the first/last observation")
        if self.start_at > self.end_at or self.end_at > self.data_as_of:
            raise ValueError("market snapshot timeline is not monotonic")
        return self


class Claim(ContractModel):
    id: Identifier
    event_id: Identifier
    signal_id: Identifier
    claim: NonEmptyString
    claim_type: Literal["narrative", "metric", "interpretation"]
    numeric_value: StrictFloat | None = None
    unit: NonEmptyString | None = None
    evidence_ids: tuple[Identifier, ...]
    counter_evidence_ids: tuple[Identifier, ...]
    created_at: AwareDatetime

    @model_validator(mode="after")
    def validate_evidence_sets(self) -> Claim:
        if not self.evidence_ids and not self.counter_evidence_ids:
            raise ValueError("a claim must reference evidence")
        supporting = set(self.evidence_ids)
        counter = set(self.counter_evidence_ids)
        if len(supporting) != len(self.evidence_ids) or len(counter) != len(
            self.counter_evidence_ids
        ):
            raise ValueError("claim evidence IDs must be unique")
        if supporting & counter:
            raise ValueError("supporting and counter evidence must be disjoint")
        if (self.numeric_value is None) != (self.unit is None):
            raise ValueError("numericValue and unit must be supplied together")
        if self.claim_type == "metric" and self.numeric_value is None:
            raise ValueError("metric claims require numericValue and unit")
        return self


class Evidence(ContractModel):
    id: Identifier
    signal_id: Identifier
    claim_id: Identifier
    evidence_type: Literal["source", "market_data", "calculation", "context"]
    supports_signal: StrictBool
    article_id: Identifier | None = None
    source_id: Identifier | None = None
    market_snapshot_ids: tuple[Identifier, ...] = ()
    source_snapshot_id: Identifier | None = None
    claim: NonEmptyString
    excerpt: NonEmptyString | None = None
    source_url: HttpUrl
    published_at: AwareDatetime | None = None
    retrieved_at: AwareDatetime
    data_as_of: AwareDatetime
    content_hash: Sha256

    @model_validator(mode="after")
    def validate_evidence_shape(self) -> Evidence:
        if self.data_as_of > self.retrieved_at:
            raise ValueError("dataAsOf must not be later than retrievedAt")
        if self.published_at is not None and self.published_at > self.retrieved_at:
            raise ValueError("publishedAt must not be later than retrievedAt")
        if self.evidence_type == "source":
            required = (
                self.article_id,
                self.source_id,
                self.source_snapshot_id,
                self.excerpt,
                self.published_at,
            )
            if any(value is None for value in required):
                raise ValueError("source evidence requires article/source snapshot metadata")
            if self.market_snapshot_ids:
                raise ValueError("source evidence cannot reference market snapshots")
        elif not self.market_snapshot_ids:
            raise ValueError("market, calculation and context evidence require marketSnapshotIds")
        if len(self.market_snapshot_ids) != len(set(self.market_snapshot_ids)):
            raise ValueError("marketSnapshotIds must be unique")
        return self


class Reviewer(ContractModel):
    id: Identifier
    name: NonEmptyString


class ReviewSummary(ContractModel):
    status: ReviewStatus
    justification: NonEmptyString | None = None
    reviewed_by: Reviewer | None = None
    reviewed_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_review_state(self) -> ReviewSummary:
        server_fields = (self.justification, self.reviewed_by, self.reviewed_at)
        if self.status == ReviewStatus.PENDING_REVIEW and any(
            value is not None for value in server_fields
        ):
            raise ValueError("pending reviews cannot contain terminal review metadata")
        if self.status != ReviewStatus.PENDING_REVIEW and any(
            value is None for value in server_fields
        ):
            raise ValueError("terminal reviews require justification, reviewedBy and reviewedAt")
        return self


class PriceReaction(ContractModel):
    asset_return: StrictFloat
    benchmark_return: StrictFloat | None = None
    abnormal_return: StrictFloat | None = None
    relative_volume: NonNegativeFloat | None = None

    @model_validator(mode="after")
    def validate_abnormal_return(self) -> PriceReaction:
        if self.benchmark_return is None:
            if self.abnormal_return is not None:
                raise ValueError("abnormalReturn requires benchmarkReturn")
            return self
        expected_abnormal = self.asset_return - self.benchmark_return
        if self.abnormal_return is None or abs(self.abnormal_return - expected_abnormal) > 1e-9:
            raise ValueError("abnormalReturn must equal assetReturn - benchmarkReturn")
        return self


class Signal(ContractModel):
    id: Identifier
    event_id: Identifier
    asset: AssetRef
    impact: Impact
    time_horizon: Literal["immediate", "short_term", "medium_term", "unknown"]
    confidence: UnitInterval
    analysis_status: AnalysisStatus
    requires_human_review: Literal[True]
    thesis: NonEmptyString | None = None
    price_reaction: PriceReaction | None = None
    evidence_ids: tuple[Identifier, ...]
    counter_evidence_ids: tuple[Identifier, ...]
    assumptions: tuple[NonEmptyString, ...]
    invalidation_conditions: tuple[NonEmptyString, ...]
    suggested_research_actions: tuple[NonEmptyString, ...]
    disclaimer: DisclaimerText
    review: ReviewSummary
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_signal_state(self) -> Signal:
        supporting = set(self.evidence_ids)
        counter = set(self.counter_evidence_ids)
        if len(supporting) != len(self.evidence_ids) or len(counter) != len(
            self.counter_evidence_ids
        ):
            raise ValueError("signal evidence IDs must be unique")
        if supporting & counter:
            raise ValueError("supporting and counter evidence must be disjoint")
        if self.created_at > self.updated_at:
            raise ValueError("createdAt must not be later than updatedAt")
        if self.analysis_status == AnalysisStatus.COMPLETED:
            if self.confidence < 0.60:
                raise ValueError("completed signals require confidence >= 0.60")
            if not self.thesis or self.price_reaction is None or not self.evidence_ids:
                raise ValueError("completed signals require thesis, priceReaction and evidence")
        if self.analysis_status in {
            AnalysisStatus.INSUFFICIENT_EVIDENCE,
            AnalysisStatus.FAILED,
        } and self.impact != Impact.UNCERTAIN:
            raise ValueError("insufficient or failed analyses must have uncertain impact")
        if self.confidence < 0.60 and self.analysis_status not in {
            AnalysisStatus.INSUFFICIENT_EVIDENCE,
            AnalysisStatus.FAILED,
        }:
            raise ValueError("confidence below 0.60 requires abstention")
        return self


class SignalReview(ContractModel):
    id: Identifier
    signal_id: Identifier
    previous_status: ReviewStatus
    status: ReviewStatus
    justification: NonEmptyString
    reviewed_by: Reviewer
    reviewed_at: AwareDatetime
    created_at: AwareDatetime

    @model_validator(mode="after")
    def validate_transition(self) -> SignalReview:
        if self.status == ReviewStatus.PENDING_REVIEW:
            raise ValueError("a review record cannot transition to pending_review")
        if self.status == self.previous_status:
            raise ValueError("a review record must change status")
        if self.reviewed_at > self.created_at:
            raise ValueError("reviewedAt must not be later than createdAt")
        return self


class WatchlistRef(ContractModel):
    id: Identifier
    name: NonEmptyString


class PrioritizedSignal(ContractModel):
    signal_id: Identifier
    priority: Literal["high", "medium", "low"]
    reason: NonEmptyString
    suggested_research_actions: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    review: ReviewSummary


class ReviewTask(ContractModel):
    id: Identifier
    signal_id: Identifier
    kind: Literal["review", "escalation"]
    status: Literal["open", "resolved"]
    title: NonEmptyString
    description: NonEmptyString
    created_at: AwareDatetime
    resolved_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_review_task(self) -> ReviewTask:
        if self.status == "open" and self.resolved_at is not None:
            raise ValueError("open review tasks cannot have resolvedAt")
        if self.status == "resolved" and self.resolved_at is None:
            raise ValueError("resolved review tasks require resolvedAt")
        if self.resolved_at is not None and self.created_at > self.resolved_at:
            raise ValueError("createdAt must not be later than resolvedAt")
        return self


class HumanReviewSummary(ContractModel):
    total_signals: NonNegativeInt
    pending_review: NonNegativeInt
    reviewed: NonNegativeInt
    escalated: NonNegativeInt
    discarded: NonNegativeInt

    @model_validator(mode="after")
    def validate_totals(self) -> HumanReviewSummary:
        subtotal = self.pending_review + self.reviewed + self.escalated + self.discarded
        if subtotal != self.total_signals:
            raise ValueError("review counters must sum to totalSignals")
        return self


class Briefing(ContractModel):
    briefing_id: Identifier
    status: BriefingStatus
    watchlist: WatchlistRef
    executive_summary: NonEmptyString
    prioritized_signals: tuple[PrioritizedSignal, ...]
    review_tasks: tuple[ReviewTask, ...] = ()
    human_review_summary: HumanReviewSummary
    requires_human_review: Literal[True]
    disclaimer: DisclaimerText
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def validate_briefing(self) -> Briefing:
        signal_ids = [item.signal_id for item in self.prioritized_signals]
        if len(signal_ids) != len(set(signal_ids)):
            raise ValueError("prioritizedSignals must not repeat signalId")
        if len(signal_ids) > self.human_review_summary.total_signals:
            raise ValueError("prioritizedSignals cannot exceed totalSignals")
        task_ids = [item.id for item in self.review_tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("reviewTasks must not repeat an id")
        task_signal_ids = {item.signal_id for item in self.review_tasks}
        if not task_signal_ids <= set(signal_ids):
            raise ValueError("reviewTasks must reference prioritized signals only")
        if self.created_at > self.updated_at:
            raise ValueError("createdAt must not be later than updatedAt")
        if self.status == BriefingStatus.SHAREABLE and (
            self.human_review_summary.pending_review
            or self.human_review_summary.escalated
            or self.human_review_summary.discarded
        ):
            raise ValueError("shareable briefings can only contain reviewed signals")
        if self.status == BriefingStatus.SHAREABLE and any(
            task.status != "resolved" for task in self.review_tasks
        ):
            raise ValueError("shareable briefings cannot contain open review tasks")
        return self


class AgentRun(ContractModel):
    id: Identifier
    organization_id: Identifier
    conversation_id: Identifier | None = None
    current_node: NonEmptyString
    status: AnalysisStatus
    model_name: NonEmptyString | None = None
    prompt_version: NonEmptyString | None = None
    input_hash: Sha256
    source_snapshot_ids: tuple[Identifier, ...]
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    error_code: NonEmptyString | None = None
    retry_count: NonNegativeInt

    @model_validator(mode="after")
    def validate_run_state(self) -> AgentRun:
        if len(self.source_snapshot_ids) != len(set(self.source_snapshot_ids)):
            raise ValueError("sourceSnapshotIds must be unique")
        if self.finished_at is not None and self.started_at > self.finished_at:
            raise ValueError("startedAt must not be later than finishedAt")
        if self.status == AnalysisStatus.PROCESSING:
            if self.finished_at is not None or self.error_code is not None:
                raise ValueError("processing runs cannot be finished or have an errorCode")
        elif self.status == AnalysisStatus.FAILED:
            if self.finished_at is None or self.error_code is None:
                raise ValueError("failed runs require finishedAt and errorCode")
        elif self.finished_at is None or self.error_code is not None:
            raise ValueError("completed runs require finishedAt and no errorCode")
        return self
