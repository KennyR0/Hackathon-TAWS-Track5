#!/usr/bin/env python3
"""Generate the deterministic, offline Phase 0 fixture graph."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_OUTPUT = REPO_ROOT / "data" / "fixtures" / "v1" / "phase0_bundle.json"
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts.entities import (  # noqa: E402
    DISCLAIMER,
    AgentRun,
    AnalysisStatus,
    Article,
    Asset,
    AssetRef,
    AssetRelation,
    Briefing,
    BriefingStatus,
    Claim,
    DataMode,
    Event,
    Evidence,
    Freshness,
    HumanReviewSummary,
    Impact,
    InstrumentType,
    MarketPoint,
    MarketSnapshot,
    PriceReaction,
    PrioritizedSignal,
    Reviewer,
    ReviewStatus,
    ReviewSummary,
    Signal,
    SignalReview,
    Source,
    SourceTier,
    WatchlistRef,
    allow_internal_field_names,
)
from app.contracts.fixtures import (  # noqa: E402
    FixtureBundle,
    FixtureManifest,
    RawSourceSnapshot,
    build_fixture_hash,
    calculation_evidence_hash_payload,
    market_snapshot_hash_payload,
    sha256_digest,
)

FIXTURE_CLOCK = datetime(2026, 7, 11, 13, 0, tzinfo=UTC)
ANALYSIS_AT = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
ZERO_HASH = f"sha256:{'0' * 64}"
FIXTURE_WARNINGS = ("FIXTURE_DATA", "NOT_REAL_TIME")
NEWS_WARNINGS = (*FIXTURE_WARNINGS, "SYNTHETIC_NEWS")


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _freshness(data_as_of: datetime, stale_after_seconds: int) -> Freshness:
    age_seconds = (FIXTURE_CLOCK - data_as_of).total_seconds()
    return Freshness(
        evaluated_at=FIXTURE_CLOCK,
        stale_after_seconds=stale_after_seconds,
        is_stale=age_seconds > stale_after_seconds,
    )


def _provenance(
    *,
    provider: str,
    retrieved_at: datetime,
    data_as_of: datetime,
    stale_after_seconds: int,
    warnings: tuple[str, ...] = FIXTURE_WARNINGS,
) -> dict[str, object]:
    return {
        "data_mode": DataMode.FIXTURE,
        "provider": provider,
        "retrieved_at": retrieved_at,
        "data_as_of": data_as_of,
        "freshness": _freshness(data_as_of, stale_after_seconds),
        "warnings": warnings,
    }


def _business_dates(end: date, count: int) -> tuple[date, ...]:
    days: list[date] = []
    cursor = end
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return tuple(reversed(days))


def _all_business_dates(start: date, end: date) -> tuple[date, ...]:
    days: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def _at_utc(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour=hour), tzinfo=UTC)


def _build_article(
    *,
    article_id: str,
    snapshot_id: str,
    source: Source,
    provider_article_id: str,
    headline: str,
    summary: str,
    published_at: datetime,
    retrieved_at: datetime,
    slug: str,
) -> tuple[Article, RawSourceSnapshot]:
    url = f"https://{source.domain}/news/{slug}"
    payload = {
        "canonicalUrl": url,
        "headline": headline,
        "isSynthetic": True,
        "originalPublisher": source.name,
        "providerArticleId": provider_article_id,
        "publishedAt": published_at.isoformat().replace("+00:00", "Z"),
        "summary": summary,
    }
    content_hash = sha256_digest(payload)
    raw_snapshot = RawSourceSnapshot(
        id=snapshot_id,
        source_id=source.id,
        provider="fixture_news_feed",
        provider_article_id=provider_article_id,
        captured_at=retrieved_at,
        payload=payload,
        content_hash=content_hash,
    )
    article = Article(
        id=article_id,
        source_id=source.id,
        provider_article_id=provider_article_id,
        headline=headline,
        summary=summary,
        published_at=published_at,
        url=url,
        language="es",
        source_snapshot_id=snapshot_id,
        content_hash=content_hash,
        is_synthetic=True,
        **_provenance(
            provider="fixture_news_feed",
            retrieved_at=retrieved_at,
            data_as_of=published_at,
            stale_after_seconds=172_800,
            warnings=NEWS_WARNINGS,
        ),
    )
    return article, raw_snapshot


def _build_market_snapshot(
    *,
    snapshot_id: str,
    asset_id: str,
    provider: str,
    interval: str,
    source_url: str,
    observations: tuple[MarketPoint, ...],
    retrieved_at: datetime,
    stale_after_seconds: int,
    benchmark_asset_id: str | None = None,
    series_id: str | None = None,
    missing_value_policy: str = "none",
) -> MarketSnapshot:
    values = {
        "id": snapshot_id,
        "asset_id": asset_id,
        "benchmark_asset_id": benchmark_asset_id,
        "series_id": series_id,
        "interval": interval,
        "currency": "USD",
        "timezone": "UTC",
        "start_at": observations[0].timestamp,
        "end_at": observations[-1].timestamp,
        "source_url": source_url,
        "observations": observations,
        "missing_value_policy": missing_value_policy,
        **_provenance(
            provider=provider,
            retrieved_at=retrieved_at,
            data_as_of=observations[-1].timestamp,
            stale_after_seconds=stale_after_seconds,
        ),
    }
    placeholder = MarketSnapshot(content_hash=ZERO_HASH, **values)
    content_hash = sha256_digest(market_snapshot_hash_payload(placeholder))
    return MarketSnapshot(content_hash=content_hash, **values)


def _source_evidence(
    *,
    evidence_id: str,
    signal_id: str,
    claim: Claim,
    article: Article,
    supports_signal: bool,
    excerpt: str,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        signal_id=signal_id,
        claim_id=claim.id,
        evidence_type="source",
        supports_signal=supports_signal,
        article_id=article.id,
        source_id=article.source_id,
        source_snapshot_id=article.source_snapshot_id,
        claim=claim.claim,
        excerpt=excerpt,
        source_url=article.url,
        published_at=article.published_at,
        retrieved_at=article.retrieved_at,
        data_as_of=article.data_as_of,
        content_hash=article.content_hash,
    )


def _market_evidence(
    *,
    evidence_id: str,
    signal_id: str,
    claim: Claim,
    snapshots: tuple[MarketSnapshot, ...],
    evidence_type: str,
) -> Evidence:
    snapshot_ids = tuple(snapshot.id for snapshot in snapshots)
    if evidence_type in {"market_data", "context"} and len(snapshots) == 1:
        content_hash = snapshots[0].content_hash
    else:
        hash_candidate = Evidence(
            id=evidence_id,
            signal_id=signal_id,
            claim_id=claim.id,
            evidence_type=evidence_type,
            supports_signal=True,
            market_snapshot_ids=snapshot_ids,
            claim=claim.claim,
            source_url="https://fixtures.nexomercado.test/methodology/event-metrics",
            retrieved_at=ANALYSIS_AT,
            data_as_of=max(snapshot.data_as_of for snapshot in snapshots),
            content_hash=ZERO_HASH,
        )
        content_hash = sha256_digest(
            calculation_evidence_hash_payload(hash_candidate, claim)
        )
    return Evidence(
        id=evidence_id,
        signal_id=signal_id,
        claim_id=claim.id,
        evidence_type=evidence_type,
        supports_signal=True,
        market_snapshot_ids=snapshot_ids,
        claim=claim.claim,
        source_url=(
            snapshots[0].source_url
            if evidence_type in {"market_data", "context"} and len(snapshots) == 1
            else "https://fixtures.nexomercado.test/methodology/event-metrics"
        ),
        retrieved_at=(
            snapshots[0].retrieved_at
            if evidence_type in {"market_data", "context"} and len(snapshots) == 1
            else ANALYSIS_AT
        ),
        data_as_of=max(snapshot.data_as_of for snapshot in snapshots),
        content_hash=content_hash,
    )


def _claim(
    *,
    claim_id: str,
    event_id: str,
    signal_id: str,
    text: str,
    evidence_ids: tuple[str, ...],
    counter_evidence_ids: tuple[str, ...] = (),
    numeric_value: float | None = None,
    unit: str | None = None,
) -> Claim:
    return Claim(
        id=claim_id,
        event_id=event_id,
        signal_id=signal_id,
        claim=text,
        claim_type="metric" if numeric_value is not None else "narrative",
        numeric_value=numeric_value,
        unit=unit,
        evidence_ids=evidence_ids,
        counter_evidence_ids=counter_evidence_ids,
        created_at=ANALYSIS_AT,
    )


def _sources() -> tuple[Source, Source]:
    return (
        Source(
            id="src_fixture_finwire",
            name="Nexo Fixture Financial Wire",
            domain="finwire-fixture.test",
            tier=SourceTier.B,
            publisher_group_id="grp_fixture_finwire",
            is_original_publisher=True,
            is_aggregator=False,
            fixture_only=True,
            homepage_url="https://finwire-fixture.test",
            country_code="US",
            language="es",
        ),
        Source(
            id="src_fixture_businessdaily",
            name="Nexo Fixture Business Daily",
            domain="businessdaily-fixture.test",
            tier=SourceTier.C,
            publisher_group_id="grp_fixture_businessdaily",
            is_original_publisher=True,
            is_aggregator=False,
            fixture_only=True,
            homepage_url="https://businessdaily-fixture.test",
            country_code="GB",
            language="es",
        ),
    )


def _assets() -> tuple[Asset, ...]:
    return (
        Asset(
            id="ast_aapl",
            symbol="AAPL",
            name="Apple Inc.",
            instrument_type=InstrumentType.EQUITY,
            currency="USD",
            exchange="NASDAQ",
            benchmark_asset_id="ast_spy",
        ),
        Asset(
            id="ast_spy",
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            instrument_type=InstrumentType.ETF,
            currency="USD",
            exchange="NYSE Arca",
        ),
        Asset(
            id="ast_btc_usd",
            symbol="BTC-USD",
            name="Bitcoin",
            instrument_type=InstrumentType.CRYPTO,
            currency="USD",
            exchange="Global",
        ),
        Asset(
            id="ast_wti",
            symbol="WTI",
            name="West Texas Intermediate Crude Oil",
            instrument_type=InstrumentType.COMMODITY,
            currency="USD",
            series_id="DCOILWTICO",
        ),
    )


def _articles_and_raw_snapshots(
    sources: tuple[Source, Source],
) -> tuple[tuple[Article, ...], tuple[RawSourceSnapshot, ...]]:
    finwire, businessdaily = sources
    specs = (
        (
            "art_aapl_finwire_20260709",
            "raw_news_aapl_finwire",
            finwire,
            "fixture-aapl-fw-20260709",
            "Apple reduce su previsión trimestral en el escenario de demostración",
            "El publisher informa una reducción de la previsión tras el cierre del mercado.",
            "2026-07-09T20:15:00Z",
            "2026-07-09T20:35:00Z",
            "aapl-outlook-20260709",
        ),
        (
            "art_aapl_businessdaily_20260709",
            "raw_news_aapl_businessdaily",
            businessdaily,
            "fixture-aapl-bd-20260709",
            "Segundo publisher confirma el ajuste de previsión de Apple",
            "Una cobertura independiente confirma el mismo ajuste trimestral sintético.",
            "2026-07-09T20:25:00Z",
            "2026-07-09T20:40:00Z",
            "aapl-outlook-confirmation-20260709",
        ),
        (
            "art_btc_finwire_20260710",
            "raw_news_btc_finwire",
            finwire,
            "fixture-btc-fw-20260710",
            "Un reporte describe como definitiva una medida regulatoria sobre Bitcoin",
            "El primer publisher presenta la medida sintética como una aprobación final.",
            "2026-07-10T12:10:00Z",
            "2026-07-10T12:35:00Z",
            "btc-policy-approval-20260710",
        ),
        (
            "art_btc_businessdaily_20260710",
            "raw_news_btc_businessdaily",
            businessdaily,
            "fixture-btc-bd-20260710",
            "Otra cobertura señala que la medida sobre Bitcoin sigue en consulta",
            "El segundo publisher contradice materialmente el carácter definitivo del anuncio.",
            "2026-07-10T12:25:00Z",
            "2026-07-10T12:40:00Z",
            "btc-policy-consultation-20260710",
        ),
        (
            "art_wti_finwire_20260710",
            "raw_news_wti_finwire",
            finwire,
            "fixture-wti-fw-20260710",
            "Productores extienden recortes temporales de oferta de crudo",
            "El publisher reporta una extensión sintética de recortes de oferta.",
            "2026-07-10T14:40:00Z",
            "2026-07-10T15:10:00Z",
            "wti-supply-cuts-20260710",
        ),
        (
            "art_wti_businessdaily_20260710",
            "raw_news_wti_businessdaily",
            businessdaily,
            "fixture-wti-bd-20260710",
            "Fuente independiente confirma la extensión de recortes de crudo",
            "La segunda cobertura corrobora el evento, sin afirmar causalidad de precio.",
            "2026-07-10T14:55:00Z",
            "2026-07-10T15:15:00Z",
            "wti-supply-cuts-confirmation-20260710",
        ),
    )
    pairs = tuple(
        _build_article(
            article_id=article_id,
            snapshot_id=snapshot_id,
            source=source,
            provider_article_id=provider_article_id,
            headline=headline,
            summary=summary,
            published_at=_dt(published_at),
            retrieved_at=_dt(retrieved_at),
            slug=slug,
        )
        for (
            article_id,
            snapshot_id,
            source,
            provider_article_id,
            headline,
            summary,
            published_at,
            retrieved_at,
            slug,
        ) in specs
    )
    return tuple(pair[0] for pair in pairs), tuple(pair[1] for pair in pairs)


def _events() -> tuple[Event, ...]:
    return (
        Event(
            id="evt_aapl_outlook_20260709",
            title="Ajuste de previsión trimestral de Apple",
            summary="Dos publishers sintéticos independientes corroboran el evento.",
            event_at=_dt("2026-07-09T20:05:00Z"),
            article_ids=(
                "art_aapl_finwire_20260709",
                "art_aapl_businessdaily_20260709",
            ),
            related_assets=(
                AssetRelation(
                    asset_id="ast_aapl",
                    symbol="AAPL",
                    relationship="direct",
                    reason="El evento sintético corresponde a la compañía emisora.",
                    entity_match_score=1.0,
                ),
                AssetRelation(
                    asset_id="ast_spy",
                    symbol="SPY",
                    relationship="sector",
                    reason="SPY es el benchmark aprobado para aislar el movimiento relativo.",
                    entity_match_score=0.9,
                ),
            ),
            created_at=_dt("2026-07-09T20:45:00Z"),
            updated_at=_dt("2026-07-09T20:45:00Z"),
            **_provenance(
                provider="fixture_news_feed",
                retrieved_at=_dt("2026-07-09T20:45:00Z"),
                data_as_of=_dt("2026-07-09T20:25:00Z"),
                stale_after_seconds=172_800,
                warnings=NEWS_WARNINGS,
            ),
        ),
        Event(
            id="evt_btc_policy_20260710",
            title="Cobertura contradictoria de una medida regulatoria sobre Bitcoin",
            summary="Dos publishers discrepan sobre si la medida sintética es definitiva.",
            event_at=_dt("2026-07-10T12:00:00Z"),
            article_ids=(
                "art_btc_finwire_20260710",
                "art_btc_businessdaily_20260710",
            ),
            related_assets=(
                AssetRelation(
                    asset_id="ast_btc_usd",
                    symbol="BTC-USD",
                    relationship="direct",
                    reason="La medida regulatoria sintética menciona directamente Bitcoin.",
                    entity_match_score=1.0,
                ),
            ),
            created_at=_dt("2026-07-10T12:45:00Z"),
            updated_at=_dt("2026-07-10T12:45:00Z"),
            **_provenance(
                provider="fixture_news_feed",
                retrieved_at=_dt("2026-07-10T12:45:00Z"),
                data_as_of=_dt("2026-07-10T12:25:00Z"),
                stale_after_seconds=172_800,
                warnings=NEWS_WARNINGS,
            ),
        ),
        Event(
            id="evt_wti_supply_20260710",
            title="Extensión temporal de recortes de oferta de crudo",
            summary="Dos publishers corroboran el evento; el precio se conserva como contexto.",
            event_at=_dt("2026-07-10T14:30:00Z"),
            article_ids=(
                "art_wti_finwire_20260710",
                "art_wti_businessdaily_20260710",
            ),
            related_assets=(
                AssetRelation(
                    asset_id="ast_wti",
                    symbol="WTI",
                    relationship="commodity",
                    reason="El evento de oferta se relaciona directamente con el crudo WTI.",
                    entity_match_score=0.98,
                ),
            ),
            created_at=_dt("2026-07-10T15:20:00Z"),
            updated_at=_dt("2026-07-10T15:20:00Z"),
            **_provenance(
                provider="fixture_news_feed",
                retrieved_at=_dt("2026-07-10T15:20:00Z"),
                data_as_of=_dt("2026-07-10T14:55:00Z"),
                stale_after_seconds=172_800,
                warnings=NEWS_WARNINGS,
            ),
        ),
    )


def _market_snapshots() -> tuple[MarketSnapshot, ...]:
    aapl_dates = _business_dates(date(2026, 7, 10), 21)
    aapl_points = tuple(
        MarketPoint(
            timestamp=_at_utc(day, 20),
            close=(210.0 if index == 19 else 201.6 if index == 20 else 200.0 + index * 0.5),
            volume=100_000_000.0 if index == 20 else 50_000_000.0,
        )
        for index, day in enumerate(aapl_dates)
    )
    spy_points = (
        MarketPoint(timestamp=_dt("2026-07-09T20:00:00Z"), close=620.0),
        MarketPoint(timestamp=_dt("2026-07-10T20:00:00Z"), close=616.28),
    )
    btc_start = date(2026, 6, 11)
    btc_points = tuple(
        MarketPoint(
            timestamp=_at_utc(btc_start + timedelta(days=index), 12),
            close=(
                105_000.0
                if index == 29
                else 107_100.0
                if index == 30
                else 98_000.0 + 200 * index
            ),
            volume=42_000.0 + 100 * index,
        )
        for index in range(31)
    )
    wti_dates = _all_business_dates(date(2026, 6, 10), date(2026, 7, 10))
    wti_points = tuple(
        MarketPoint(
            timestamp=_at_utc(day, 0),
            close=round(68.0 + (72.76 - 68.0) * index / (len(wti_dates) - 1), 4),
        )
        for index, day in enumerate(wti_dates)
    )
    return (
        _build_market_snapshot(
            snapshot_id="mkt_aapl_1d_20260710",
            asset_id="ast_aapl",
            benchmark_asset_id="ast_spy",
            provider="twelve_data",
            interval="1d",
            source_url="https://fixtures.nexomercado.test/market/twelve-data/aapl.json",
            observations=aapl_points,
            retrieved_at=_dt("2026-07-10T20:15:00Z"),
            stale_after_seconds=86_400,
        ),
        _build_market_snapshot(
            snapshot_id="mkt_spy_1d_20260710",
            asset_id="ast_spy",
            provider="twelve_data",
            interval="1d",
            source_url="https://fixtures.nexomercado.test/market/twelve-data/spy.json",
            observations=spy_points,
            retrieved_at=_dt("2026-07-10T20:15:00Z"),
            stale_after_seconds=86_400,
        ),
        _build_market_snapshot(
            snapshot_id="mkt_btc_1d_20260711",
            asset_id="ast_btc_usd",
            provider="coingecko",
            interval="1d",
            source_url="https://fixtures.nexomercado.test/market/coingecko/btc-usd.json",
            observations=btc_points,
            retrieved_at=_dt("2026-07-11T12:05:00Z"),
            stale_after_seconds=3_600,
        ),
        _build_market_snapshot(
            snapshot_id="mkt_wti_1d_20260710",
            asset_id="ast_wti",
            provider="fred",
            interval="1d",
            series_id="DCOILWTICO",
            source_url="https://fixtures.nexomercado.test/market/fred/dcoilwtico.json",
            observations=wti_points,
            retrieved_at=_dt("2026-07-11T01:00:00Z"),
            stale_after_seconds=172_800,
            missing_value_policy="skip_non_trading_days",
        ),
    )


def _claims() -> tuple[Claim, ...]:
    return (
        _claim(
            claim_id="clm_aapl_event",
            event_id="evt_aapl_outlook_20260709",
            signal_id="sig_aapl_negative",
            text=(
                "Dos publishers independientes informan una reducción de la previsión "
                "trimestral de Apple."
            ),
            evidence_ids=("evd_aapl_finwire", "evd_aapl_businessdaily"),
        ),
        _claim(
            claim_id="clm_aapl_asset_return",
            event_id="evt_aapl_outlook_20260709",
            signal_id="sig_aapl_negative",
            text="AAPL cayó 4 % entre el cierre anterior y el primer cierre posterior.",
            evidence_ids=("evd_aapl_asset_return",),
            numeric_value=-0.04,
            unit="decimal_return",
        ),
        _claim(
            claim_id="clm_aapl_benchmark_return",
            event_id="evt_aapl_outlook_20260709",
            signal_id="sig_aapl_negative",
            text="SPY cayó 0,6 % en la misma ventana de cierres.",
            evidence_ids=("evd_aapl_benchmark_return",),
            numeric_value=-0.006,
            unit="decimal_return",
        ),
        _claim(
            claim_id="clm_aapl_abnormal_return",
            event_id="evt_aapl_outlook_20260709",
            signal_id="sig_aapl_negative",
            text="El retorno anormal simplificado de AAPL frente a SPY fue -3,4 %.",
            evidence_ids=("evd_aapl_abnormal_return",),
            numeric_value=-0.034,
            unit="decimal_return",
        ),
        _claim(
            claim_id="clm_aapl_relative_volume",
            event_id="evt_aapl_outlook_20260709",
            signal_id="sig_aapl_negative",
            text="El volumen de AAPL fue 2 veces la media de las 20 sesiones previas.",
            evidence_ids=("evd_aapl_relative_volume",),
            numeric_value=2.0,
            unit="ratio",
        ),
        _claim(
            claim_id="clm_btc_policy_status",
            event_id="evt_btc_policy_20260710",
            signal_id="sig_btc_uncertain",
            text="La medida regulatoria sobre Bitcoin quedó aprobada de forma definitiva.",
            evidence_ids=("evd_btc_finwire_support",),
            counter_evidence_ids=("evd_btc_businessdaily_counter",),
        ),
        _claim(
            claim_id="clm_btc_24h_return",
            event_id="evt_btc_policy_20260710",
            signal_id="sig_btc_uncertain",
            text="BTC-USD subió 2 % durante las 24 horas posteriores al evento.",
            evidence_ids=("evd_btc_market",),
            numeric_value=0.02,
            unit="decimal_return",
        ),
        _claim(
            claim_id="clm_wti_supply_event",
            event_id="evt_wti_supply_20260710",
            signal_id="sig_wti_context",
            text=(
                "Dos publishers independientes informan una extensión temporal de "
                "recortes de oferta de crudo."
            ),
            evidence_ids=("evd_wti_finwire", "evd_wti_businessdaily"),
        ),
        _claim(
            claim_id="clm_wti_30d_change",
            event_id="evt_wti_supply_20260710",
            signal_id="sig_wti_context",
            text="WTI subió 7 % en la ventana de 30 días usada como contexto.",
            evidence_ids=("evd_wti_market",),
            numeric_value=0.07,
            unit="decimal_return",
        ),
    )


def _evidence(
    claims: tuple[Claim, ...],
    articles: tuple[Article, ...],
    snapshots: tuple[MarketSnapshot, ...],
) -> tuple[Evidence, ...]:
    claim_by_id = {item.id: item for item in claims}
    article_by_id = {item.id: item for item in articles}
    snapshot_by_id = {item.id: item for item in snapshots}
    return (
        _source_evidence(
            evidence_id="evd_aapl_finwire",
            signal_id="sig_aapl_negative",
            claim=claim_by_id["clm_aapl_event"],
            article=article_by_id["art_aapl_finwire_20260709"],
            supports_signal=True,
            excerpt="El escenario reduce la previsión trimestral después del cierre.",
        ),
        _source_evidence(
            evidence_id="evd_aapl_businessdaily",
            signal_id="sig_aapl_negative",
            claim=claim_by_id["clm_aapl_event"],
            article=article_by_id["art_aapl_businessdaily_20260709"],
            supports_signal=True,
            excerpt="La cobertura independiente confirma el mismo ajuste sintético.",
        ),
        _market_evidence(
            evidence_id="evd_aapl_asset_return",
            signal_id="sig_aapl_negative",
            claim=claim_by_id["clm_aapl_asset_return"],
            snapshots=(snapshot_by_id["mkt_aapl_1d_20260710"],),
            evidence_type="calculation",
        ),
        _market_evidence(
            evidence_id="evd_aapl_benchmark_return",
            signal_id="sig_aapl_negative",
            claim=claim_by_id["clm_aapl_benchmark_return"],
            snapshots=(snapshot_by_id["mkt_spy_1d_20260710"],),
            evidence_type="calculation",
        ),
        _market_evidence(
            evidence_id="evd_aapl_abnormal_return",
            signal_id="sig_aapl_negative",
            claim=claim_by_id["clm_aapl_abnormal_return"],
            snapshots=(
                snapshot_by_id["mkt_aapl_1d_20260710"],
                snapshot_by_id["mkt_spy_1d_20260710"],
            ),
            evidence_type="calculation",
        ),
        _market_evidence(
            evidence_id="evd_aapl_relative_volume",
            signal_id="sig_aapl_negative",
            claim=claim_by_id["clm_aapl_relative_volume"],
            snapshots=(snapshot_by_id["mkt_aapl_1d_20260710"],),
            evidence_type="calculation",
        ),
        _source_evidence(
            evidence_id="evd_btc_finwire_support",
            signal_id="sig_btc_uncertain",
            claim=claim_by_id["clm_btc_policy_status"],
            article=article_by_id["art_btc_finwire_20260710"],
            supports_signal=True,
            excerpt="El primer publisher describe la medida como una aprobación final.",
        ),
        _source_evidence(
            evidence_id="evd_btc_businessdaily_counter",
            signal_id="sig_btc_uncertain",
            claim=claim_by_id["clm_btc_policy_status"],
            article=article_by_id["art_btc_businessdaily_20260710"],
            supports_signal=False,
            excerpt="El segundo publisher afirma que la medida sigue en consulta.",
        ),
        _market_evidence(
            evidence_id="evd_btc_market",
            signal_id="sig_btc_uncertain",
            claim=claim_by_id["clm_btc_24h_return"],
            snapshots=(snapshot_by_id["mkt_btc_1d_20260711"],),
            evidence_type="market_data",
        ),
        _source_evidence(
            evidence_id="evd_wti_finwire",
            signal_id="sig_wti_context",
            claim=claim_by_id["clm_wti_supply_event"],
            article=article_by_id["art_wti_finwire_20260710"],
            supports_signal=True,
            excerpt="La cobertura reporta una extensión temporal de recortes de oferta.",
        ),
        _source_evidence(
            evidence_id="evd_wti_businessdaily",
            signal_id="sig_wti_context",
            claim=claim_by_id["clm_wti_supply_event"],
            article=article_by_id["art_wti_businessdaily_20260710"],
            supports_signal=True,
            excerpt="La fuente independiente corrobora el evento sin atribuir causalidad.",
        ),
        _market_evidence(
            evidence_id="evd_wti_market",
            signal_id="sig_wti_context",
            claim=claim_by_id["clm_wti_30d_change"],
            snapshots=(snapshot_by_id["mkt_wti_1d_20260710"],),
            evidence_type="context",
        ),
    )


def _signals(reviewer: Reviewer) -> tuple[Signal, ...]:
    reviewed_at = _dt("2026-07-11T12:30:00Z")
    return (
        Signal(
            id="sig_aapl_negative",
            event_id="evt_aapl_outlook_20260709",
            asset=AssetRef(
                symbol="AAPL",
                name="Apple Inc.",
                instrument_type=InstrumentType.EQUITY,
            ),
            impact=Impact.NEGATIVE,
            time_horizon="short_term",
            confidence=0.81,
            analysis_status=AnalysisStatus.COMPLETED,
            requires_human_review=True,
            thesis=(
                "El ajuste corroborado coincide con una reacción negativa de AAPL superior "
                "a la de SPY; la relación no demuestra causalidad por sí sola."
            ),
            price_reaction=PriceReaction(
                asset_return=-0.04,
                benchmark_return=-0.006,
                abnormal_return=-0.034,
                relative_volume=2.0,
            ),
            evidence_ids=(
                "evd_aapl_finwire",
                "evd_aapl_businessdaily",
                "evd_aapl_asset_return",
                "evd_aapl_benchmark_return",
                "evd_aapl_abnormal_return",
                "evd_aapl_relative_volume",
            ),
            counter_evidence_ids=(),
            assumptions=("El primer cierre posterior es una ventana válida para el evento.",),
            invalidation_conditions=(
                "El ajuste se revierte o se demuestra que el movimiento precedió al evento.",
            ),
            suggested_research_actions=(
                "Contrastar el ajuste con el documento corporativo oficial.",
            ),
            disclaimer=DISCLAIMER,
            review=ReviewSummary(
                status=ReviewStatus.REVIEWED,
                justification="La evidencia y los cálculos reproducibles fueron verificados.",
                reviewed_by=reviewer,
                reviewed_at=reviewed_at,
            ),
            created_at=ANALYSIS_AT,
            updated_at=_dt("2026-07-11T12:31:00Z"),
        ),
        Signal(
            id="sig_btc_uncertain",
            event_id="evt_btc_policy_20260710",
            asset=AssetRef(
                symbol="BTC-USD",
                name="Bitcoin",
                instrument_type=InstrumentType.CRYPTO,
            ),
            impact=Impact.UNCERTAIN,
            time_horizon="immediate",
            confidence=0.4,
            analysis_status=AnalysisStatus.INSUFFICIENT_EVIDENCE,
            requires_human_review=True,
            thesis=(
                "La reacción de 24 horas es observable, pero la contradicción material impide "
                "clasificar el impacto del anuncio."
            ),
            price_reaction=PriceReaction(asset_return=0.02),
            evidence_ids=("evd_btc_finwire_support", "evd_btc_market"),
            counter_evidence_ids=("evd_btc_businessdaily_counter",),
            assumptions=("La ventana de 24 horas está completa.",),
            invalidation_conditions=("Una fuente primaria aclara el estado regulatorio.",),
            suggested_research_actions=(
                "Localizar la resolución regulatoria primaria antes de reclasificar.",
            ),
            disclaimer=DISCLAIMER,
            review=ReviewSummary(status=ReviewStatus.PENDING_REVIEW),
            created_at=ANALYSIS_AT,
            updated_at=ANALYSIS_AT,
        ),
        Signal(
            id="sig_wti_context",
            event_id="evt_wti_supply_20260710",
            asset=AssetRef(
                symbol="WTI",
                name="West Texas Intermediate Crude Oil",
                instrument_type=InstrumentType.COMMODITY,
            ),
            impact=Impact.POSITIVE,
            time_horizon="short_term",
            confidence=0.72,
            analysis_status=AnalysisStatus.COMPLETED,
            requires_human_review=True,
            thesis=(
                "La extensión corroborada coincide con un avance de 7 % del WTI en 30 días, "
                "usado únicamente como contexto y no como prueba causal."
            ),
            price_reaction=PriceReaction(asset_return=0.07),
            evidence_ids=("evd_wti_finwire", "evd_wti_businessdaily", "evd_wti_market"),
            counter_evidence_ids=(),
            assumptions=("La serie diaria omite días sin publicación.",),
            invalidation_conditions=(
                "Datos posteriores muestran que el cambio antecedió completamente al evento.",
            ),
            suggested_research_actions=(
                "Comparar el evento con inventarios y demanda antes de atribuir causalidad.",
            ),
            disclaimer=DISCLAIMER,
            review=ReviewSummary(status=ReviewStatus.PENDING_REVIEW),
            created_at=ANALYSIS_AT,
            updated_at=ANALYSIS_AT,
        ),
    )


def _signal_reviews(reviewer: Reviewer) -> tuple[SignalReview, ...]:
    return (
        SignalReview(
            id="rev_aapl_001",
            signal_id="sig_aapl_negative",
            previous_status=ReviewStatus.PENDING_REVIEW,
            status=ReviewStatus.REVIEWED,
            justification="La evidencia y los cálculos reproducibles fueron verificados.",
            reviewed_by=reviewer,
            reviewed_at=_dt("2026-07-11T12:30:00Z"),
            created_at=_dt("2026-07-11T12:31:00Z"),
        ),
    )


def _briefing(signals: tuple[Signal, ...]) -> Briefing:
    priorities = ("high", "high", "medium")
    reasons = (
        "Movimiento anormal y volumen relativo elevados.",
        "Contradicción material que requiere resolución humana.",
        "Evento corroborado con cambio de 30 días solo contextual.",
    )
    return Briefing(
        briefing_id="brf_demo_global_20260711",
        status=BriefingStatus.DRAFT,
        watchlist=WatchlistRef(id="watchlist_demo_global", name="Demo Global"),
        executive_summary=(
            "El corpus contiene una señal revisada, una abstención por contradicción y una "
            "señal contextual pendiente."
        ),
        prioritized_signals=tuple(
            PrioritizedSignal(
                signal_id=signal.id,
                priority=priority,
                reason=reason,
                suggested_research_actions=signal.suggested_research_actions,
                review=signal.review,
            )
            for signal, priority, reason in zip(signals, priorities, reasons, strict=True)
        ),
        human_review_summary=HumanReviewSummary(
            total_signals=3,
            pending_review=2,
            reviewed=1,
            escalated=0,
            discarded=0,
        ),
        requires_human_review=True,
        disclaimer=DISCLAIMER,
        created_at=_dt("2026-07-11T12:45:00Z"),
        updated_at=_dt("2026-07-11T12:45:00Z"),
    )


def _agent_run(source_snapshot_ids: Iterable[str]) -> AgentRun:
    return AgentRun(
        id="run_phase0_fixture_001",
        organization_id="org_demo",
        conversation_id=None,
        current_node="pending_review",
        status=AnalysisStatus.COMPLETED,
        model_name="fixture-deterministic",
        prompt_version="phase0-v1",
        input_hash=sha256_digest(
            {
                "fixtureClock": FIXTURE_CLOCK.isoformat().replace("+00:00", "Z"),
                "scenarioIds": [
                    "evt_aapl_outlook_20260709",
                    "evt_btc_policy_20260710",
                    "evt_wti_supply_20260710",
                ],
            }
        ),
        source_snapshot_ids=tuple(source_snapshot_ids),
        started_at=_dt("2026-07-11T10:00:00Z"),
        finished_at=ANALYSIS_AT,
        error_code=None,
        retry_count=0,
    )


def _build_bundle() -> FixtureBundle:
    sources = _sources()
    assets = _assets()
    articles, raw_snapshots = _articles_and_raw_snapshots(sources)
    events = _events()
    market_snapshots = _market_snapshots()
    claims = _claims()
    evidence = _evidence(claims, articles, market_snapshots)
    reviewer = Reviewer(id="usr_analista_demo", name="Analista Demo")
    signals = _signals(reviewer)
    signal_reviews = _signal_reviews(reviewer)
    briefings = (_briefing(signals),)
    agent_runs = (
        _agent_run(
            (
                *(snapshot.id for snapshot in raw_snapshots),
                *(snapshot.id for snapshot in market_snapshots),
            )
        ),
    )
    values = {
        "sources": sources,
        "articles": articles,
        "events": events,
        "assets": assets,
        "market_snapshots": market_snapshots,
        "claims": claims,
        "evidence": evidence,
        "signals": signals,
        "signal_reviews": signal_reviews,
        "briefings": briefings,
        "agent_runs": agent_runs,
        "raw_source_snapshots": raw_snapshots,
    }
    provisional_manifest = FixtureManifest(
        fixture_id="fixture_phase0_v1",
        schema_version="1.0.0",
        fixture_clock=FIXTURE_CLOCK,
        generator_version="1.0.0",
        fixture_hash=ZERO_HASH,
    )
    provisional = FixtureBundle.model_construct(manifest=provisional_manifest, **values)
    manifest = FixtureManifest(
        fixture_id=provisional_manifest.fixture_id,
        schema_version=provisional_manifest.schema_version,
        fixture_clock=provisional_manifest.fixture_clock,
        generator_version=provisional_manifest.generator_version,
        fixture_hash=build_fixture_hash(provisional),
    )
    return FixtureBundle(manifest=manifest, **values)


def build_bundle() -> FixtureBundle:
    with allow_internal_field_names():
        return _build_bundle()


def rendered_bundle(bundle: FixtureBundle) -> bytes:
    return (
        bundle.model_dump_json(
            by_alias=True,
            indent=2,
            exclude_computed_fields=True,
        )
        + "\n"
    ).encode("utf-8")


def write_bundle(bundle: FixtureBundle, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rendered_bundle(bundle))
    FixtureBundle.model_validate_json(output.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the committed bundle differs.",
    )
    args = parser.parse_args()
    bundle = build_bundle()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != rendered_bundle(bundle):
            print(f"Fixture bundle is stale: {args.output}", file=sys.stderr)
            return 1
        print(f"Fixture bundle is current: {args.output}")
        return 0
    write_bundle(bundle, args.output)
    print(
        f"Generated {args.output}: {len(bundle.events)} events, "
        f"{len(bundle.signals)} signals, {len(bundle.evidence)} evidence records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
