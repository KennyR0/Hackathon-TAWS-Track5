"""Build a sanitized, auditable view of the configured market providers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from app.contracts.api import (
    ProviderRuntimeCheck,
    ProviderRuntimeResponse,
    ProviderRuntimeStatus,
)
from app.contracts.entities import (
    DataMode,
    DataProvenance,
    Freshness,
    allow_internal_field_names,
)
from app.providers.base import ProviderProbeResult
from app.providers.live_market import MarketDataRuntimeService, MarketRuntimeSnapshot

RESOURCE_LABELS: Final[dict[str, str]] = {
    "news": "Noticias Apple",
    "aapl": "AAPL",
    "spy": "SPY",
    "btc": "BTC-USD",
    "wti": "DCOILWTICO",
}

PROVIDERS_BY_KEY: Final[dict[str, str]] = {
    "news": "gdelt",
    "aapl": "twelve_data",
    "spy": "finnhub",
    "btc": "coingecko",
    "wti": "fred",
}

ALLOWED_METRICS: Final[dict[str, frozenset[str]]] = {
    "news": frozenset(
        {
            "articleCount",
            "titles",
            "query",
            "error",
            "attempts",
            "retryable",
            "statusCode",
            "circuitOpen",
            "servedFromCache",
            "cacheFetchedAt",
        }
    ),
    "aapl": frozenset(
        {
            "symbol",
            "close",
            "currency",
            "error",
            "attempts",
            "retryable",
            "statusCode",
            "circuitOpen",
            "servedFromCache",
            "cacheFetchedAt",
        }
    ),
    "spy": frozenset(
        {
            "symbol",
            "current",
            "previousClose",
            "error",
            "attempts",
            "retryable",
            "statusCode",
            "circuitOpen",
            "servedFromCache",
            "cacheFetchedAt",
        }
    ),
    "btc": frozenset(
        {
            "symbol",
            "usd",
            "lastUpdatedAt",
            "error",
            "attempts",
            "retryable",
            "statusCode",
            "circuitOpen",
            "servedFromCache",
            "cacheFetchedAt",
        }
    ),
    "wti": frozenset(
        {
            "seriesId",
            "value",
            "date",
            "error",
            "attempts",
            "retryable",
            "statusCode",
            "requestBudget",
            "requestsUsed",
            "circuitOpen",
            "servedFromCache",
            "cacheFetchedAt",
        }
    ),
}


class ProviderDemoService:
    def __init__(self, runtime: MarketDataRuntimeService) -> None:
        self._runtime = runtime

    def get_status(self) -> ProviderRuntimeResponse:
        try:
            snapshot = self._runtime.collect_demo_snapshot()
        except Exception as exc:
            snapshot = _build_runtime_unavailable_snapshot(
                configured_mode=self._runtime.mode,
                exc=exc,
            )
        checked_at = datetime.now(UTC)
        checks = tuple(
            _build_check(key, result, checked_at=checked_at)
            for key, result in snapshot.checks.items()
        )
        effective_mode = DataMode(snapshot.data_mode)
        with allow_internal_field_names():
            freshness = Freshness(
                evaluated_at=checked_at,
                stale_after_seconds=300,
                is_stale=False,
            )
            meta = DataProvenance(
                data_mode=effective_mode,
                provider=snapshot.provider,
                retrieved_at=checked_at,
                data_as_of=checked_at,
                freshness=freshness,
                warnings=snapshot.warnings,
            )
            status = ProviderRuntimeStatus(
                checked_at=checked_at,
                configured_mode=self._runtime.mode,
                effective_data_mode=effective_mode,
                provider=snapshot.provider,
                request_budget=snapshot.request_budget,
                requests_used=snapshot.requests_used,
                checks=checks,
                warnings=snapshot.warnings,
            )
            return ProviderRuntimeResponse(data=status, meta=meta)


def _build_check(
    key: str,
    result: ProviderProbeResult,
    *,
    checked_at: datetime,
) -> ProviderRuntimeCheck:
    if key not in RESOURCE_LABELS or key not in ALLOWED_METRICS:
        raise ValueError(f"Unsupported provider runtime check: {key}")
    sanitized = {
        name: value
        for name, value in result.payload.items()
        if name in ALLOWED_METRICS[key]
    }
    with allow_internal_field_names():
        return ProviderRuntimeCheck(
            key=key,
            provider=result.provider,
            resource=RESOURCE_LABELS[key],
            data_mode=DataMode(result.data_mode),
            ok=result.ok,
            metrics=sanitized,
            data_as_of=_resolve_data_as_of(key, sanitized, checked_at),
            warnings=result.warnings,
        )


def _resolve_data_as_of(
    key: str,
    metrics: dict[str, object],
    checked_at: datetime,
) -> datetime | None:
    cache_fetched_at = metrics.get("cacheFetchedAt")
    if isinstance(cache_fetched_at, str):
        try:
            return datetime.fromisoformat(cache_fetched_at.replace("Z", "+00:00"))
        except ValueError:
            return None
    if key == "btc":
        updated_at = metrics.get("lastUpdatedAt")
        if isinstance(updated_at, (int, float)):
            return datetime.fromtimestamp(updated_at, tz=UTC)
        return None
    if key == "wti":
        observed_on = metrics.get("date")
        if isinstance(observed_on, str):
            try:
                return datetime.fromisoformat(observed_on).replace(tzinfo=UTC)
            except ValueError:
                return None
        return None
    return checked_at if metrics and "error" not in metrics else None


def _build_runtime_unavailable_snapshot(
    *,
    configured_mode: str,
    exc: Exception,
) -> MarketRuntimeSnapshot:
    warnings = (
        "PROVIDER_RUNTIME_STATUS_UNAVAILABLE",
        "PROVIDER_RUNTIME_STORE_UNAVAILABLE",
    )
    checks = {
        key: ProviderProbeResult(
            provider=provider,
            data_mode=DataMode.FALLBACK.value,
            ok=False,
            warnings=warnings,
            payload={
                "error": type(exc).__name__,
                "retryable": True,
            },
        )
        for key, provider in PROVIDERS_BY_KEY.items()
    }
    return MarketRuntimeSnapshot(
        data_mode=DataMode.FALLBACK.value,
        provider="+".join(PROVIDERS_BY_KEY.values()),
        warnings=warnings,
        checks=checks,
        request_budget=0 if configured_mode == DataMode.FIXTURE.value else 8,
        requests_used=0,
    )


__all__ = ["ProviderDemoService"]
