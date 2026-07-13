"""Live provider adapters and runtime fallback orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import sleep

import httpx

from app.config import MarketProviderConfig
from app.contracts.entities import DataMode, DataProvenance, Freshness, allow_internal_field_names
from app.providers.base import (
    CachedProviderProbe,
    FixtureDataProvider,
    MacroProvider,
    NewsProvider,
    PriceProvider,
    ProviderCacheStore,
    ProviderProbeResult,
)
from app.services.provider_runtime_service import ProviderRuntimeBundle, store_probe_cache

FIXTURE_WARNINGS: tuple[str, ...] = ("FIXTURE_DATA", "NOT_REAL_TIME")
DEFAULT_REQUEST_BUDGET = 8
DEFAULT_RETRY_LIMIT = 1
DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 1
RETRYABLE_HTTP_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
RUNTIME_STORE_UNAVAILABLE_WARNING = "PROVIDER_RUNTIME_STORE_UNAVAILABLE"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _fallback_result(
    provider: str,
    *,
    payload: dict[str, object],
    warning: str | tuple[str, ...],
) -> ProviderProbeResult:
    warnings = (warning,) if isinstance(warning, str) else warning
    return ProviderProbeResult(
        provider=provider,
        data_mode=DataMode.FALLBACK.value,
        ok=False,
        warnings=warnings,
        payload=payload,
    )


def _live_result(provider: str, payload: dict[str, object]) -> ProviderProbeResult:
    return ProviderProbeResult(
        provider=provider,
        data_mode=DataMode.LIVE.value,
        ok=True,
        warnings=(),
        payload=payload,
    )


def _add_warning(result: ProviderProbeResult, warning: str | None) -> ProviderProbeResult:
    if warning is None or warning in result.warnings:
        return result
    return ProviderProbeResult(
        provider=result.provider,
        data_mode=result.data_mode,
        ok=result.ok,
        warnings=(*result.warnings, warning),
        payload=result.payload,
    )


class GDELTNewsProvider(NewsProvider):
    def __init__(
        self,
        *,
        base_url: str,
        user_agent: str,
        timeout_seconds: float,
        max_attempts: int,
        client: httpx.Client | None = None,
        sleep_fn=sleep,
    ) -> None:
        self._base_url = base_url
        self._max_attempts = max_attempts
        self._sleep = sleep_fn
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            headers={
                "Accept": "application/json",
                "User-Agent": user_agent,
            },
        )

    def probe(self) -> ProviderProbeResult:
        request_params = {
            "query": "Apple",
            "mode": "ArtList",
            "maxrecords": 1,
            "format": "json",
            "sort": "datedesc",
            "timespan": "1day",
        }
        response: httpx.Response | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.get(self._base_url, params=request_params)
                response.raise_for_status()
                break
            except httpx.TimeoutException:
                if attempt >= self._max_attempts:
                    raise
                self._sleep(0.2 * attempt)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_HTTP_STATUS_CODES or attempt >= self._max_attempts:
                    raise
                self._sleep(0.2 * attempt)
        if response is None:
            raise RuntimeError("GDELT probe failed to produce a response")
        payload = response.json()
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            raise ValueError("GDELT response did not include a valid articles list")
        return _live_result(
            "gdelt",
            {
                "articleCount": len(articles),
                "titles": [item.get("title") for item in articles[:3]],
                "query": request_params["query"],
            },
        )


class TwelveDataPriceProvider(PriceProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, symbol: str) -> ProviderProbeResult:
        if not self._api_key:
            return _fallback_result(
                "twelve_data",
                payload={"symbol": symbol},
                warning="TWELVE_DATA_KEY_MISSING",
            )
        response = self._client.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": symbol, "apikey": self._api_key},
        )
        response.raise_for_status()
        payload = response.json()
        return _live_result(
            "twelve_data",
            {"symbol": symbol, "close": payload.get("close"), "currency": payload.get("currency")},
        )


class CoinGeckoPriceProvider(PriceProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, symbol: str) -> ProviderProbeResult:
        params = {
            "ids": "bitcoin",
            "vs_currencies": "usd",
            "include_last_updated_at": "true",
        }
        headers = {}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key
        response = self._client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json().get("bitcoin", {})
        return _live_result(
            "coingecko",
            {
                "symbol": symbol,
                "usd": payload.get("usd"),
                "lastUpdatedAt": payload.get("last_updated_at"),
            },
        )


class FREDMacroProvider(MacroProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, series_id: str) -> ProviderProbeResult:
        if not self._api_key:
            return _fallback_result(
                "fred",
                payload={"seriesId": series_id},
                warning="FRED_KEY_MISSING",
            )
        response = self._client.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "limit": 2,
                "sort_order": "desc",
            },
        )
        response.raise_for_status()
        observations = response.json().get("observations", [])
        latest = observations[0] if observations else {}
        return _live_result(
            "fred",
            {"seriesId": series_id, "value": latest.get("value"), "date": latest.get("date")},
        )


class FinnhubMarketProvider(PriceProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, symbol: str) -> ProviderProbeResult:
        if not self._api_key:
            return _fallback_result(
                "finnhub",
                payload={"symbol": symbol},
                warning="FINNHUB_KEY_MISSING",
            )
        response = self._client.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": self._api_key},
        )
        response.raise_for_status()
        payload = response.json()
        return _live_result(
            "finnhub",
            {"symbol": symbol, "current": payload.get("c"), "previousClose": payload.get("pc")},
        )


@dataclass(frozen=True)
class MarketRuntimeSnapshot:
    data_mode: str
    provider: str
    warnings: tuple[str, ...]
    checks: dict[str, ProviderProbeResult]
    request_budget: int
    requests_used: int


class MarketDataRuntimeService:
    def __init__(
        self,
        config: MarketProviderConfig,
        fixture_provider: FixtureDataProvider,
        *,
        news_provider: NewsProvider | None = None,
        equity_price_provider: PriceProvider | None = None,
        crypto_price_provider: PriceProvider | None = None,
        macro_provider: MacroProvider | None = None,
        metadata_provider: PriceProvider | None = None,
        provider_cache: ProviderCacheStore | None = None,
        request_budget: int = DEFAULT_REQUEST_BUDGET,
        retry_limit: int = DEFAULT_RETRY_LIMIT,
        circuit_breaker_failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        provider_runtime: ProviderRuntimeBundle | None = None,
    ) -> None:
        self._config = config
        self._fixture_provider = fixture_provider
        self._provider_cache = provider_cache
        self._request_budget = max(0, request_budget)
        self._retry_limit = max(0, retry_limit)
        self._circuit_breaker_failure_threshold = max(1, circuit_breaker_failure_threshold)
        self._provider_runtime = provider_runtime
        self._failed_provider_counts: dict[str, int] = {}
        self._requests_used = 0
        self._news_provider = news_provider or GDELTNewsProvider(
            base_url=config.gdelt_base_url,
            user_agent=config.gdelt_user_agent,
            timeout_seconds=config.gdelt_timeout_seconds,
            max_attempts=config.gdelt_max_attempts,
        )
        self._equity_price_provider = equity_price_provider or TwelveDataPriceProvider(
            config.twelve_data_api_key
        )
        self._crypto_price_provider = crypto_price_provider or CoinGeckoPriceProvider(
            config.coingecko_api_key
        )
        self._macro_provider = macro_provider or FREDMacroProvider(config.fred_api_key)
        self._metadata_provider = metadata_provider or FinnhubMarketProvider(config.finnhub_api_key)

    @property
    def mode(self) -> str:
        return self._config.mode

    def repository_provenance(self, fixture_clock: datetime) -> DataProvenance:
        with allow_internal_field_names():
            freshness = Freshness(
                evaluated_at=fixture_clock,
                stale_after_seconds=86_400,
                is_stale=False,
            )
            if self._config.mode == DataMode.FIXTURE.value:
                return DataProvenance(
                    data_mode=DataMode.FIXTURE,
                    provider="fixture_repository",
                    retrieved_at=fixture_clock,
                    data_as_of=fixture_clock,
                    freshness=freshness,
                    warnings=FIXTURE_WARNINGS,
                )
            return DataProvenance(
                data_mode=DataMode.FALLBACK,
                provider="fixture_repository_fallback",
                retrieved_at=fixture_clock,
                data_as_of=fixture_clock,
                freshness=freshness,
                warnings=("LIVE_MODE_ACTIVE_USING_FIXTURE_FALLBACK",),
            )

    def collect_demo_snapshot(self) -> MarketRuntimeSnapshot:
        checks: dict[str, ProviderProbeResult] = {}
        warnings: list[str] = []
        provider_names: list[str] = []
        self._requests_used = 0

        for key, provider_call in (
            (
                "news",
                lambda: self._safe_probe(
                    self._news_provider.probe,
                    "gdelt",
                    cache_key="news_probe:gdelt:apple",
                    resource_type="news_probe",
                    cache_ttl_seconds=self._config.gdelt_cache_ttl_seconds,
                ),
            ),
            (
                "aapl",
                lambda: self._safe_probe(
                    lambda: self._equity_price_provider.probe("AAPL"), "twelve_data"
                ),
            ),
            (
                "spy",
                lambda: self._safe_probe(
                    lambda: self._metadata_provider.probe("SPY"), "finnhub"
                ),
            ),
            (
                "btc",
                lambda: self._safe_probe(
                    lambda: self._crypto_price_provider.probe("BTC-USD"), "coingecko"
                ),
            ),
            (
                "wti",
                lambda: self._safe_probe(
                    lambda: self._macro_provider.probe("DCOILWTICO"), "fred"
                ),
            ),
        ):
            result = provider_call()
            checks[key] = result
            provider_names.append(result.provider)
            warnings.extend(result.warnings)

        all_live = all(result.ok for result in checks.values())
        if self._config.mode == DataMode.FIXTURE.value:
            effective_mode = DataMode.FIXTURE.value
            warnings = list(FIXTURE_WARNINGS)
        elif all_live:
            effective_mode = DataMode.LIVE.value
        else:
            effective_mode = DataMode.FALLBACK.value
            if not warnings:
                warnings.append("LIVE_FETCH_FAILED_FALLBACK_ACTIVE")

        return MarketRuntimeSnapshot(
            data_mode=effective_mode,
            provider="+".join(dict.fromkeys(provider_names)),
            warnings=tuple(dict.fromkeys(warnings)),
            checks=checks,
            request_budget=self._request_budget,
            requests_used=self._requests_used,
        )

    def _cache_probe_result(
        self,
        *,
        cache_key: str,
        provider: str,
        resource_type: str,
        result: ProviderProbeResult,
        cache_ttl_seconds: int,
    ) -> None:
        if self._provider_cache is None or not result.ok:
            return
        captured_at = _utc_now()
        self._provider_cache.write(
            CachedProviderProbe(
                cache_key=cache_key,
                provider=provider,
                resource_type=resource_type,
                probe=result,
                retrieved_at=captured_at,
                data_as_of=captured_at,
                expires_at=captured_at + timedelta(seconds=cache_ttl_seconds),
            )
        )

    def _build_cached_fallback(
        self,
        *,
        provider: str,
        cache_entry: CachedProviderProbe,
        failure_warning: str,
        failure_payload: dict[str, object],
    ) -> ProviderProbeResult:
        return _fallback_result(
            provider,
            payload={
                **cache_entry.probe.payload,
                "servedFromCache": True,
                "cache": {
                    "retrievedAt": cache_entry.retrieved_at.isoformat(),
                    "dataAsOf": cache_entry.data_as_of.isoformat(),
                    "expiresAt": cache_entry.expires_at.isoformat(),
                },
                "fallbackReason": failure_payload,
            },
            warning=(failure_warning, f"{provider.upper()}_CACHED_FALLBACK_ACTIVE"),
        )

    def _safe_probe(
        self,
        probe: Callable[[], ProviderProbeResult],
        provider: str,
        *,
        cache_key: str | None = None,
        resource_type: str | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> ProviderProbeResult:
        if self._config.mode == DataMode.FIXTURE.value:
            return _fallback_result(
                provider,
                payload={"mode": DataMode.FIXTURE.value},
                warning="FIXTURE_MODE_FORCES_OFFLINE_DATA",
            )
        runtime_cache_key = f"probe:{provider}"
        runtime = self._provider_runtime
        runtime_store_warning: str | None = None
        if runtime is not None:
            try:
                cached = runtime.cache.get_valid(provider, runtime_cache_key)
                if cached is not None:
                    return ProviderProbeResult(
                        provider=provider,
                        data_mode=cached.data_mode,
                        ok=cached.status_code < 400,
                        warnings=(f"{provider.upper()}_CACHE_HIT",),
                        payload={
                            **cached.response_json,
                            "servedFromCache": True,
                            "cacheFetchedAt": cached.fetched_at.isoformat(),
                        },
                    )
                if runtime.health.is_circuit_open(provider):
                    return _fallback_result(
                        provider,
                        payload={"circuitOpen": True},
                        warning=f"{provider.upper()}_CIRCUIT_OPEN",
                    )
                if not runtime.budget.try_consume(provider):
                    return _fallback_result(
                        provider,
                        payload={"requestBudget": self._request_budget},
                        warning=f"{provider.upper()}_BUDGET_EXHAUSTED",
                    )
                self._requests_used += 1
            except Exception:
                runtime = None
                runtime_store_warning = RUNTIME_STORE_UNAVAILABLE_WARNING

        if runtime is None and self._is_circuit_open(provider):
            return _add_warning(
                _fallback_result(
                    provider,
                    payload={"circuitOpen": True},
                    warning=f"{provider.upper()}_CIRCUIT_OPEN",
                ),
                runtime_store_warning,
            )
        if runtime is None and self._request_budget <= 0:
            return _add_warning(
                _fallback_result(
                    provider,
                    payload={
                        "requestBudget": self._request_budget,
                        "requestsUsed": self._requests_used,
                    },
                    warning=f"{provider.upper()}_BUDGET_EXHAUSTED",
                ),
                runtime_store_warning,
            )

        last_exc: Exception | None = None
        for attempt in range(1, self._retry_limit + 2):
            if runtime is None and self._requests_used >= self._request_budget:
                return _add_warning(
                    _fallback_result(
                        provider,
                        payload={
                            "attempts": attempt - 1,
                            "requestBudget": self._request_budget,
                            "requestsUsed": self._requests_used,
                        },
                        warning=f"{provider.upper()}_BUDGET_EXHAUSTED",
                    ),
                    runtime_store_warning,
                )
            if runtime is None:
                self._requests_used += 1
            try:
                result = probe()
            except Exception as exc:
                last_exc = exc
                if self._should_retry_exception(exc, attempt):
                    continue
                break
            if not result.ok:
                if runtime is not None:
                    try:
                        runtime.health.record_failure(
                            provider,
                            error_code=result.warnings[0] if result.warnings else "ProviderFallback",
                        )
                    except Exception:
                        runtime_store_warning = RUNTIME_STORE_UNAVAILABLE_WARNING
                        self._record_provider_failure(provider)
                else:
                    self._record_provider_failure(provider)
                return _add_warning(result, runtime_store_warning)
            if result.ok:
                if runtime is not None:
                    try:
                        runtime.health.record_success(provider)
                        store_probe_cache(
                            runtime,
                            provider=provider,
                            cache_key=runtime_cache_key,
                            params={"provider": provider},
                            response_json=result.payload,
                            status_code=200,
                            data_mode=result.data_mode,
                        )
                    except Exception:
                        runtime_store_warning = RUNTIME_STORE_UNAVAILABLE_WARNING
                        self._failed_provider_counts.pop(provider, None)
                else:
                    self._failed_provider_counts.pop(provider, None)
                    if (
                        cache_key is not None
                        and resource_type is not None
                        and cache_ttl_seconds is not None
                    ):
                        self._cache_probe_result(
                            cache_key=cache_key,
                            provider=provider,
                            resource_type=resource_type,
                            result=result,
                            cache_ttl_seconds=cache_ttl_seconds,
                        )
                return _add_warning(result, runtime_store_warning)

        if runtime is not None:
            try:
                runtime.health.record_failure(
                    provider,
                    error_code=type(last_exc).__name__ if last_exc is not None else "UnknownError",
                )
            except Exception:
                runtime_store_warning = RUNTIME_STORE_UNAVAILABLE_WARNING
                self._record_provider_failure(provider)
        else:
            self._record_provider_failure(provider)
        return _add_warning(
            self._fallback_from_exception(
                provider,
                last_exc,
                cache_key=cache_key,
            ),
            runtime_store_warning,
        )

    def _should_retry_exception(self, exc: Exception, attempt: int) -> bool:
        if attempt >= self._retry_limit + 1:
            return False
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in RETRYABLE_HTTP_STATUS_CODES
        return True

    def _fallback_from_exception(
        self,
        provider: str,
        exc: Exception | None,
        *,
        cache_key: str | None,
    ) -> ProviderProbeResult:
        if isinstance(exc, httpx.TimeoutException):
            failure_payload = {
                "error": "TimeoutException",
                "retryable": True,
                "attempts": self._retry_limit + 1,
            }
            return self._fallback_from_cache_or_error(
                provider,
                cache_key=cache_key,
                failure_warning=f"{provider.upper()}_TIMEOUT_FALLBACK_ACTIVE",
                failure_payload=failure_payload,
            )
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            warning = f"{provider.upper()}_HTTP_ERROR_FALLBACK_ACTIVE"
            if status_code == 429:
                warning = f"{provider.upper()}_RATE_LIMIT_FALLBACK_ACTIVE"
            elif status_code >= 500:
                warning = f"{provider.upper()}_UPSTREAM_FALLBACK_ACTIVE"
            failure_payload = {
                "error": "HTTPStatusError",
                "statusCode": status_code,
                "retryable": status_code in RETRYABLE_HTTP_STATUS_CODES,
                "attempts": self._retry_limit + 1,
            }
            return self._fallback_from_cache_or_error(
                provider,
                cache_key=cache_key,
                failure_warning=warning,
                failure_payload=failure_payload,
            )
        if isinstance(exc, ValueError):
            failure_payload = {"error": type(exc).__name__, "retryable": False}
            return self._fallback_from_cache_or_error(
                provider,
                cache_key=cache_key,
                failure_warning=f"{provider.upper()}_PAYLOAD_INVALID_FALLBACK_ACTIVE",
                failure_payload=failure_payload,
            )
        failure_payload = {
            "error": type(exc).__name__ if exc is not None else "UnknownError",
            "attempts": self._retry_limit + 1,
            "retryable": False,
        }
        return self._fallback_from_cache_or_error(
            provider,
            cache_key=cache_key,
            failure_warning=f"{provider.upper()}_FALLBACK_ACTIVE",
            failure_payload=failure_payload,
        )

    def _fallback_from_cache_or_error(
        self,
        provider: str,
        *,
        cache_key: str | None,
        failure_warning: str,
        failure_payload: dict[str, object],
    ) -> ProviderProbeResult:
        if cache_key is not None and self._provider_cache is not None:
            cache_entry = self._provider_cache.read(cache_key)
            if cache_entry is not None:
                return self._build_cached_fallback(
                    provider=provider,
                    cache_entry=cache_entry,
                    failure_warning=failure_warning,
                    failure_payload=failure_payload,
                )
        return _fallback_result(
            provider,
            payload=failure_payload,
            warning=failure_warning,
        )

    def _is_circuit_open(self, provider: str) -> bool:
        return (
            self._failed_provider_counts.get(provider, 0)
            >= self._circuit_breaker_failure_threshold
        )

    def _record_provider_failure(self, provider: str) -> None:
        self._failed_provider_counts[provider] = self._failed_provider_counts.get(provider, 0) + 1
