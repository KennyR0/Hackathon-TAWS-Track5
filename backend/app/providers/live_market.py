"""Live provider adapters and runtime fallback orchestration."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import partial
from time import sleep

import httpx

from app.config import MarketProviderConfig
from app.contracts.entities import DataMode, DataProvenance, Freshness, allow_internal_field_names
from app.news_resolution import resolve_news_probe
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
BUSINESS_NEWS_QUERY = (
    '("Apple" OR "Microsoft" OR "NVIDIA" OR "Amazon" OR "Alphabet" OR "Meta" '
    'OR "Tesla" OR "JPMorgan" OR "Bank of America" OR "Visa" OR "Walmart" '
    'OR "Costco" OR "Exxon" OR "Chevron" OR "UnitedHealth" OR "Johnson & Johnson" '
    'OR "Pfizer" OR "Coca-Cola" OR "Disney" OR "Netflix")'
)
DEFAULT_REQUEST_BUDGET = 8
DEFAULT_RETRY_LIMIT = 1
DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 1
RETRYABLE_HTTP_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
RUNTIME_STORE_UNAVAILABLE_WARNING = "PROVIDER_RUNTIME_STORE_UNAVAILABLE"


def _configured_api_keys(
    primary: str | None,
    configured: Sequence[str],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*((primary,) if primary else ()), *configured)))


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


def _merge_failover_results(
    primary: ProviderProbeResult,
    fallback: ProviderProbeResult,
    *,
    failover_warning: str,
) -> ProviderProbeResult:
    warnings = tuple(
        dict.fromkeys((*primary.warnings, *fallback.warnings, failover_warning))
    )
    if fallback.ok:
        return ProviderProbeResult(
            provider=fallback.provider,
            data_mode=fallback.data_mode,
            ok=True,
            warnings=warnings,
            payload=fallback.payload,
        )

    primary_is_cached = primary.payload.get("servedFromCache") is True
    fallback_is_cached = fallback.payload.get("servedFromCache") is True
    selected = fallback if fallback_is_cached and not primary_is_cached else primary
    return ProviderProbeResult(
        provider=selected.provider,
        data_mode=DataMode.FALLBACK.value,
        ok=False,
        warnings=warnings,
        payload=selected.payload,
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
            "query": BUSINESS_NEWS_QUERY,
            "mode": "ArtList",
            "maxrecords": 50,
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
                "articles": articles[:50],
            },
        )


class FinnhubNewsProvider(NewsProvider):
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self) -> ProviderProbeResult:
        today = _utc_now().date()
        response = self._client.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": "AAPL",
                "from": (today - timedelta(days=1)).isoformat(),
                "to": today.isoformat(),
                "token": self._api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Finnhub response did not include a valid news list")
        return _live_result(
            "finnhub_news",
            {
                "articleCount": len(payload),
                "titles": [item.get("headline") for item in payload[:3]],
                "query": "AAPL",
                "articles": payload[:50],
            },
        )


class TwelveDataPriceProvider(PriceProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, symbol: str) -> ProviderProbeResult:
        result = self.probe_many((symbol,))
        quotes = result.payload.get("quotes", {})
        quote = quotes.get(symbol, {}) if isinstance(quotes, dict) else {}
        if not result.ok or not isinstance(quote, dict):
            return _fallback_result(
                "twelve_data",
                payload={"symbol": symbol},
                warning=result.warnings or "TWELVE_DATA_QUOTE_UNAVAILABLE",
            )
        return _live_result("twelve_data", quote)

    def probe_many(self, symbols: tuple[str, ...]) -> ProviderProbeResult:
        if not self._api_key:
            return _fallback_result(
                "twelve_data",
                payload={"symbols": list(symbols)},
                warning="TWELVE_DATA_KEY_MISSING",
            )
        response = self._client.get(
            "https://api.twelvedata.com/quote",
            params={"symbol": ",".join(symbols), "apikey": self._api_key},
        )
        response.raise_for_status()
        payload = response.json()
        raw_quotes = payload if len(symbols) > 1 else {symbols[0]: payload}
        quotes = {
            symbol: {
                "symbol": symbol,
                "close": quote.get("close"),
                "currency": quote.get("currency"),
            }
            for symbol, quote in raw_quotes.items()
            if symbol in symbols and isinstance(quote, dict)
        }
        return _live_result(
            "twelve_data",
            {"quotes": quotes},
        )


class CoinGeckoPriceProvider(PriceProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, symbol: str) -> ProviderProbeResult:
        result = self.probe_many((symbol,))
        quotes = result.payload.get("quotes", {})
        quote = quotes.get(symbol, {}) if isinstance(quotes, dict) else {}
        if not result.ok or not isinstance(quote, dict):
            return _fallback_result(
                "coingecko",
                payload={"symbol": symbol},
                warning=result.warnings or "COINGECKO_QUOTE_UNAVAILABLE",
            )
        return _live_result("coingecko", quote)

    def probe_many(self, symbols: tuple[str, ...]) -> ProviderProbeResult:
        coin_ids = {"BTC-USD": "bitcoin", "ETH-USD": "ethereum"}
        requested = {symbol: coin_ids[symbol] for symbol in symbols if symbol in coin_ids}
        if len(requested) != len(symbols):
            return _fallback_result(
                "coingecko",
                payload={"symbols": list(symbols)},
                warning="COINGECKO_SYMBOL_UNSUPPORTED",
            )
        params = {
            "ids": ",".join(requested.values()),
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
        payload = response.json()
        quotes = {
            symbol: {
                "symbol": symbol,
                "usd": payload.get(coin_id, {}).get("usd"),
                "lastUpdatedAt": payload.get(coin_id, {}).get("last_updated_at"),
            }
            for symbol, coin_id in requested.items()
        }
        return _live_result(
            "coingecko",
            {"quotes": quotes},
        )


class RapidAPIYHFinanceProvider(PriceProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        api_host: str | None,
        base_url: str | None,
        history_path: str = "/api/v2/markets/stock/history",
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_host = api_host
        self._base_url = base_url.rstrip("/") if base_url else None
        self._history_path = history_path
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, symbol: str) -> ProviderProbeResult:
        result = self.probe_many((symbol,))
        quotes = result.payload.get("quotes", {})
        quote = quotes.get(symbol, {}) if isinstance(quotes, dict) else {}
        if not isinstance(quote, dict):
            return _fallback_result(
                "rapidapi_yh_finance",
                payload={"symbol": symbol},
                warning=result.warnings or "RAPIDAPI_YH_FINANCE_HISTORY_UNAVAILABLE",
            )
        if not result.ok:
            return ProviderProbeResult(
                provider=result.provider,
                data_mode=result.data_mode,
                ok=False,
                warnings=result.warnings,
                payload=quote,
            )
        return _live_result("rapidapi_yh_finance", quote)

    def probe_many(self, symbols: tuple[str, ...]) -> ProviderProbeResult:
        if not self._api_key or not self._api_host or not self._base_url:
            return _fallback_result(
                "rapidapi_yh_finance",
                payload={"symbols": list(symbols)},
                warning="RAPIDAPI_YH_FINANCE_CONFIG_MISSING",
            )
        raw_histories: dict[str, dict[str, object]] = {}
        has_provider_failure = False
        for symbol in symbols:
            response = self._client.get(
                f"{self._base_url}{self._history_path}",
                headers={
                    "X-RapidAPI-Key": self._api_key,
                    "X-RapidAPI-Host": self._api_host,
                },
                params={
                    "symbol": symbol,
                    "interval": "1d",
                    "limit": 30,
                },
            )
            response.raise_for_status()
            raw_response = response.json()
            if isinstance(raw_response, dict) and raw_response.get("success") is False:
                has_provider_failure = True
            raw_histories[symbol] = {
                "symbol": symbol,
                "interval": "1d",
                "limit": 30,
                "rawResponse": raw_response,
            }
        if has_provider_failure:
            return _fallback_result(
                "rapidapi_yh_finance",
                payload={"quotes": raw_histories},
                warning="RAPIDAPI_YH_FINANCE_NO_DATA_FALLBACK_ACTIVE",
            )
        return _live_result("rapidapi_yh_finance", {"quotes": raw_histories})


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


class EIAMacroProvider(MacroProvider):
    def __init__(self, api_key: str | None, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self, series_id: str) -> ProviderProbeResult:
        if series_id not in {"DCOILWTICO", "RWTC"}:
            return _fallback_result(
                "eia",
                payload={"seriesId": series_id},
                warning="EIA_SERIES_UNSUPPORTED",
            )
        if not self._api_key:
            return _fallback_result(
                "eia",
                payload={"seriesId": "RWTC"},
                warning="EIA_KEY_MISSING",
            )
        response = self._client.get(
            "https://api.eia.gov/v2/petroleum/pri/spt/data/",
            params={
                "api_key": self._api_key,
                "frequency": "daily",
                "data[0]": "value",
                "facets[series][]": "RWTC",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "offset": 0,
                "length": 1,
            },
        )
        response.raise_for_status()
        payload = response.json().get("response", {})
        observations = payload.get("data", []) if isinstance(payload, dict) else []
        latest = observations[0] if isinstance(observations, list) and observations else None
        if not isinstance(latest, dict) or latest.get("value") in {None, ""}:
            raise ValueError("EIA response did not include a valid RWTC observation")
        return _live_result(
            "eia",
            {
                "seriesId": "RWTC",
                "value": latest.get("value"),
                "date": latest.get("period"),
            },
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
        news_fallback_provider: NewsProvider | None = None,
        news_fallback_providers: Sequence[NewsProvider] | None = None,
        equity_price_provider: PriceProvider | None = None,
        equity_price_providers: Sequence[PriceProvider] | None = None,
        crypto_price_provider: PriceProvider | None = None,
        crypto_price_providers: Sequence[PriceProvider] | None = None,
        crypto_fallback_provider: PriceProvider | None = None,
        macro_provider: MacroProvider | None = None,
        macro_providers: Sequence[MacroProvider] | None = None,
        macro_fallback_provider: MacroProvider | None = None,
        metadata_provider: PriceProvider | None = None,
        metadata_providers: Sequence[PriceProvider] | None = None,
        provider_cache: ProviderCacheStore | None = None,
        request_budget: int = DEFAULT_REQUEST_BUDGET,
        retry_limit: int = DEFAULT_RETRY_LIMIT,
        circuit_breaker_failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        provider_runtime: ProviderRuntimeBundle | None = None,
        persisted_news_loader: Callable[[int], Sequence[dict[str, object]]] | None = None,
    ) -> None:
        self._config = config
        self._fixture_provider = fixture_provider
        self._provider_cache = provider_cache
        self._persisted_news_loader = persisted_news_loader
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
        finnhub_keys = _configured_api_keys(config.finnhub_api_key, config.finnhub_api_keys)
        twelve_data_keys = _configured_api_keys(
            config.twelve_data_api_key,
            config.twelve_data_api_keys,
        )
        coingecko_keys = _configured_api_keys(
            config.coingecko_api_key,
            config.coingecko_api_keys,
        )
        fred_keys = _configured_api_keys(config.fred_api_key, config.fred_api_keys)
        self._news_fallback_providers = (
            tuple(news_fallback_providers)
            if news_fallback_providers is not None
            else (
                (news_fallback_provider,)
                if news_fallback_provider is not None
                else tuple(FinnhubNewsProvider(key) for key in finnhub_keys)
            )
        )
        self._equity_price_providers = (
            tuple(equity_price_providers)
            if equity_price_providers is not None
            else (
                (equity_price_provider,)
                if equity_price_provider is not None
                else tuple(TwelveDataPriceProvider(key) for key in twelve_data_keys)
                or (TwelveDataPriceProvider(None),)
            )
        )
        self._crypto_price_providers = (
            tuple(crypto_price_providers)
            if crypto_price_providers is not None
            else (
                (crypto_price_provider,)
                if crypto_price_provider is not None
                else tuple(CoinGeckoPriceProvider(key) for key in coingecko_keys)
                or (CoinGeckoPriceProvider(None),)
            )
        )
        self._crypto_fallback_provider = crypto_fallback_provider or RapidAPIYHFinanceProvider(
            api_key=config.rapidapi_key,
            api_host=config.yahoo_finance_api_host,
            base_url=config.yahoo_finance_base_url,
            history_path=config.yahoo_finance_history_path,
        )
        self._macro_providers = (
            tuple(macro_providers)
            if macro_providers is not None
            else (
                (macro_provider,)
                if macro_provider is not None
                else tuple(FREDMacroProvider(key) for key in fred_keys)
                or (FREDMacroProvider(None),)
            )
        )
        self._macro_fallback_provider = macro_fallback_provider or EIAMacroProvider(
            config.eia_api_key
        )
        self._metadata_providers = (
            tuple(metadata_providers)
            if metadata_providers is not None
            else (
                (metadata_provider,)
                if metadata_provider is not None
                else tuple(FinnhubMarketProvider(key) for key in finnhub_keys)
                or (FinnhubMarketProvider(None),)
            )
        )

    @property
    def mode(self) -> str:
        return self._config.mode

    @property
    def provider_runtime(self) -> ProviderRuntimeBundle | None:
        return self._provider_runtime

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

    def _probe_credential_chain(
        self,
        probes: Sequence[Callable[[], ProviderProbeResult]],
        provider: str,
        *,
        cache_key: str,
        request_cost: int = 1,
        resource_type: str | None = None,
        cache_ttl_seconds: int | None = None,
    ) -> ProviderProbeResult:
        if not probes:
            return _fallback_result(
                provider,
                payload={"configuredKeys": 0},
                warning=f"{provider.upper()}_KEY_MISSING",
            )
        result: ProviderProbeResult | None = None
        has_multiple_keys = len(probes) > 1
        for index, probe in enumerate(probes, start=1):
            runtime_provider = (
                f"{provider}_key_{index}" if has_multiple_keys else provider
            )
            current = self._safe_probe(
                probe,
                runtime_provider,
                cache_key=(
                    f"{cache_key}:key:{index}" if has_multiple_keys else cache_key
                ),
                resource_type=resource_type,
                cache_ttl_seconds=cache_ttl_seconds,
                request_cost=request_cost,
            )
            if result is None:
                result = current
            else:
                result = _merge_failover_results(
                    result,
                    current,
                    failover_warning=(
                        f"{provider.upper()}_KEY_{index - 1}_TO_KEY_{index}_FAILOVER"
                    ),
                )
            if current.ok:
                return result
        assert result is not None
        return result

    def collect_quotes(self, instruments) -> dict[str, ProviderProbeResult]:
        """Collect budgeted quotes for validated universe instruments."""

        self._requests_used = 0
        results: dict[str, ProviderProbeResult] = {}
        equities = tuple(
            item for item in instruments if item.instrument_type.value in {"equity", "etf"}
        )
        cryptos = tuple(item for item in instruments if item.instrument_type.value == "crypto")
        batch_groups = (
            (equities, self._equity_price_providers, "twelve_data"),
            (cryptos, self._crypto_price_providers, "coingecko"),
        )
        for group, price_providers, provider_name in batch_groups:
            if not group:
                continue
            symbols = tuple(item.symbol for item in group)
            batch_probes = tuple(
                partial(probe_many, symbols)
                for price_provider in price_providers
                if callable(probe_many := getattr(price_provider, "probe_many", None))
            )
            if len(batch_probes) == len(price_providers):
                batch = self._probe_credential_chain(
                    batch_probes,
                    provider_name,
                    cache_key=f"probe:{provider_name}:quotes:{','.join(symbols)}",
                    request_cost=len(symbols) if provider_name == "twelve_data" else 1,
                )
                quotes = batch.payload.get("quotes", {})
                for symbol in symbols:
                    quote = quotes.get(symbol) if isinstance(quotes, dict) else None
                    if batch.ok and isinstance(quote, dict):
                        results[symbol] = ProviderProbeResult(
                            provider=batch.provider,
                            data_mode=batch.data_mode,
                            ok=True,
                            warnings=batch.warnings,
                            payload=quote,
                        )
                    else:
                        results[symbol] = _fallback_result(
                            provider_name,
                            payload={"symbol": symbol},
                            warning=batch.warnings or f"{provider_name.upper()}_QUOTE_UNAVAILABLE",
                        )
            else:
                for symbol in symbols:
                    results[symbol] = self._probe_credential_chain(
                        tuple(
                            partial(price_provider.probe, symbol)
                            for price_provider in price_providers
                        ),
                        provider_name,
                        cache_key=f"probe:{provider_name}:quote:{symbol}",
                    )

        for instrument in instruments:
            symbol = instrument.symbol
            if instrument.series_id:
                series_id = instrument.series_id
                primary = self._probe_credential_chain(
                    tuple(
                        partial(provider.probe, series_id)
                        for provider in self._macro_providers
                    ),
                    "fred",
                    cache_key=f"probe:fred:series:{series_id}",
                )
                if primary.ok:
                    results[symbol] = primary
                    continue
                fallback = self._safe_probe(
                    partial(self._macro_fallback_provider.probe, series_id),
                    "eia",
                    cache_key="probe:eia:series:RWTC",
                )
                results[symbol] = _merge_failover_results(
                    primary,
                    fallback,
                    failover_warning="FRED_TO_EIA_FAILOVER",
                )

        for instrument in equities:
            symbol = instrument.symbol
            result = results[symbol]
            if not result.ok:
                fallback = self._probe_credential_chain(
                    tuple(
                        partial(provider.probe, symbol)
                        for provider in self._metadata_providers
                    ),
                    "finnhub",
                    cache_key=f"probe:finnhub:quote:{symbol}",
                )
                if fallback.ok:
                    result = ProviderProbeResult(
                        provider=fallback.provider,
                        data_mode=fallback.data_mode,
                        ok=True,
                        warnings=tuple(
                            dict.fromkeys((*result.warnings, "TWELVE_DATA_TO_FINNHUB_FAILOVER"))
                        ),
                        payload=fallback.payload,
                    )
                if not result.ok:
                    yahoo = self._safe_probe(
                        partial(self._crypto_fallback_provider.probe, symbol),
                        "rapidapi_yh_finance",
                        cache_key=f"probe:rapidapi_yh_finance:history:{symbol}",
                    )
                    result = _merge_failover_results(
                        result,
                        yahoo,
                        failover_warning="FINNHUB_TO_RAPIDAPI_YH_FINANCE_FAILOVER",
                    )
                results[symbol] = result

        failed_cryptos = tuple(item for item in cryptos if not results[item.symbol].ok)
        if failed_cryptos:
            symbols = tuple(item.symbol for item in failed_cryptos)
            probe_many = getattr(self._crypto_fallback_provider, "probe_many", None)
            if callable(probe_many):
                batch = self._safe_probe(
                    partial(probe_many, symbols),
                    "rapidapi_yh_finance",
                    cache_key=f"probe:rapidapi_yh_finance:history:{','.join(symbols)}",
                    request_cost=len(symbols),
                )
                quotes = batch.payload.get("quotes", {})
                for symbol in symbols:
                    quote = quotes.get(symbol) if isinstance(quotes, dict) else None
                    fallback = (
                        ProviderProbeResult(
                            provider=batch.provider,
                            data_mode=batch.data_mode,
                            ok=True,
                            warnings=batch.warnings,
                            payload=quote,
                        )
                        if batch.ok and isinstance(quote, dict)
                        else ProviderProbeResult(
                            provider=batch.provider,
                            data_mode=DataMode.FALLBACK.value,
                            ok=False,
                            warnings=batch.warnings
                            or ("RAPIDAPI_YH_FINANCE_HISTORY_UNAVAILABLE",),
                            payload=batch.payload,
                        )
                    )
                    results[symbol] = _merge_failover_results(
                        results[symbol],
                        fallback,
                        failover_warning="COINGECKO_TO_RAPIDAPI_YH_FINANCE_FAILOVER",
                    )
        for instrument in instruments:
            symbol = instrument.symbol
            if not results[symbol].ok:
                results[symbol] = self._fixture_quote_fallback(symbol, results[symbol])
        return results

    def collect_universe_snapshot(self, instruments) -> MarketRuntimeSnapshot:
        checks = self.collect_quotes(instruments)
        warnings = tuple(
            dict.fromkeys(warning for result in checks.values() for warning in result.warnings)
        )
        all_live = bool(checks) and all(
            result.ok and result.data_mode == DataMode.LIVE.value for result in checks.values()
        )
        if self._config.mode == DataMode.FIXTURE.value:
            effective_mode = DataMode.FIXTURE.value
            warnings = FIXTURE_WARNINGS
        elif all_live:
            effective_mode = DataMode.LIVE.value
        else:
            effective_mode = DataMode.FALLBACK.value
            if not warnings:
                warnings = ("LIVE_FETCH_FAILED_FALLBACK_ACTIVE",)
        return MarketRuntimeSnapshot(
            data_mode=effective_mode,
            provider="+".join(dict.fromkeys(result.provider for result in checks.values())),
            warnings=warnings,
            checks=checks,
            request_budget=self._request_budget,
            requests_used=self._requests_used,
        )

    def collect_demo_snapshot(self) -> MarketRuntimeSnapshot:
        checks: dict[str, ProviderProbeResult] = {}
        warnings: list[str] = []
        provider_names: list[str] = []
        self._requests_used = 0

        for key, provider_call in (
            (
                "news",
                self._probe_news,
            ),
            (
                "aapl",
                lambda: self._probe_equity("AAPL"),
            ),
            (
                "spy",
                lambda: self._probe_credential_chain(
                    tuple(
                        partial(provider.probe, "SPY")
                        for provider in self._metadata_providers
                    ),
                    "finnhub",
                    cache_key="probe:finnhub:quote:SPY",
                ),
            ),
            (
                "btc",
                lambda: self._probe_crypto("BTC-USD"),
            ),
            (
                "wti",
                lambda: self._probe_macro("DCOILWTICO"),
            ),
        ):
            result = provider_call()
            checks[key] = result
            provider_names.append(result.provider)
            warnings.extend(result.warnings)

        all_live = all(
            result.ok and result.data_mode == DataMode.LIVE.value for result in checks.values()
        )
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

    def _probe_equity(self, symbol: str) -> ProviderProbeResult:
        primary = self._probe_credential_chain(
            tuple(
                partial(provider.probe, symbol)
                for provider in self._equity_price_providers
            ),
            "twelve_data",
            cache_key=f"probe:twelve_data:quote:{symbol}",
        )
        if primary.ok:
            return primary
        fallback = self._probe_credential_chain(
            tuple(
                partial(provider.probe, symbol)
                for provider in self._metadata_providers
            ),
            "finnhub",
            cache_key=f"probe:finnhub:quote:{symbol}",
        )
        result = _merge_failover_results(
            primary,
            fallback,
            failover_warning="TWELVE_DATA_TO_FINNHUB_FAILOVER",
        )
        if not result.ok:
            yahoo = self._safe_probe(
                partial(self._crypto_fallback_provider.probe, symbol),
                "rapidapi_yh_finance",
                cache_key=f"probe:rapidapi_yh_finance:history:{symbol}",
            )
            result = _merge_failover_results(
                result,
                yahoo,
                failover_warning="FINNHUB_TO_RAPIDAPI_YH_FINANCE_FAILOVER",
            )
        return self._fixture_quote_fallback(symbol, result)

    def _probe_crypto(self, symbol: str) -> ProviderProbeResult:
        primary = self._probe_credential_chain(
            tuple(
                partial(provider.probe, symbol)
                for provider in self._crypto_price_providers
            ),
            "coingecko",
            cache_key=f"probe:coingecko:price:{symbol}",
        )
        if primary.ok:
            return primary
        fallback = self._safe_probe(
            partial(self._crypto_fallback_provider.probe, symbol),
            "rapidapi_yh_finance",
            cache_key=f"probe:rapidapi_yh_finance:history:{symbol}",
        )
        result = _merge_failover_results(
            primary,
            fallback,
            failover_warning="COINGECKO_TO_RAPIDAPI_YH_FINANCE_FAILOVER",
        )
        return self._fixture_quote_fallback(symbol, result)

    def _probe_macro(self, series_id: str) -> ProviderProbeResult:
        primary = self._probe_credential_chain(
            tuple(
                partial(provider.probe, series_id)
                for provider in self._macro_providers
            ),
            "fred",
            cache_key=f"probe:fred:series:{series_id}",
        )
        if primary.ok:
            return primary
        fallback = self._safe_probe(
            partial(self._macro_fallback_provider.probe, series_id),
            "eia",
            cache_key="probe:eia:series:RWTC",
        )
        result = _merge_failover_results(
            primary,
            fallback,
            failover_warning="FRED_TO_EIA_FAILOVER",
        )
        return self._fixture_quote_fallback("WTI", result)

    def _probe_news(self) -> ProviderProbeResult:
        fallback_providers = self._news_fallback_providers
        return resolve_news_probe(
            probe_primary=lambda: self._safe_probe(
                self._news_provider.probe,
                "gdelt",
                cache_key="probe:gdelt:news:apple",
                resource_type="news_probe",
                cache_ttl_seconds=self._config.gdelt_cache_ttl_seconds,
            ),
            probe_fallback=(
                (lambda: self._probe_credential_chain(
                    tuple(provider.probe for provider in fallback_providers),
                    "finnhub",
                    cache_key="probe:finnhub:company_news:AAPL",
                ))
                if fallback_providers
                else None
            ),
            load_persisted=self._persisted_news_loader,
            fixture_fallback=self._fixture_news_fallback,
        )

    def _fixture_quote_fallback(
        self,
        symbol: str,
        result: ProviderProbeResult,
    ) -> ProviderProbeResult:
        try:
            bundle = self._fixture_provider.load_bundle()
            asset = next(item for item in bundle.assets if item.symbol == symbol)
            snapshots = tuple(
                item for item in bundle.market_snapshots if item.asset_id == asset.id
            )
            snapshot = max(snapshots, key=lambda item: item.end_at)
            latest = snapshot.observations[-1]
            previous = snapshot.observations[-2]
        except (AttributeError, LookupError, StopIteration, ValueError, TypeError):
            return result
        return ProviderProbeResult(
            provider="fixture_market",
            data_mode=DataMode.FALLBACK.value,
            ok=False,
            warnings=tuple(
                dict.fromkeys((*result.warnings, "FIXTURE_QUOTE_FALLBACK_ACTIVE"))
            ),
            payload={
                "symbol": symbol,
                "close": latest.close,
                "previousClose": previous.close,
                "dataAsOf": snapshot.data_as_of.isoformat(),
                "sourceSnapshotId": snapshot.id,
            },
        )

    def _fixture_news_fallback(
        self,
        result: ProviderProbeResult,
    ) -> ProviderProbeResult:
        try:
            bundle = self._fixture_provider.load_bundle()
            articles = tuple(bundle.articles[:50])
        except (AttributeError, LookupError, TypeError):
            return result
        return ProviderProbeResult(
            provider="fixture_news",
            data_mode=DataMode.FALLBACK.value,
            ok=False,
            warnings=tuple(
                dict.fromkeys((*result.warnings, "FIXTURE_NEWS_FALLBACK_ACTIVE"))
            ),
            payload={
                "articleCount": len(articles),
                "titles": [article.headline for article in articles[:3]],
                "articles": [
                    article.model_dump(mode="json", by_alias=True) for article in articles
                ],
            },
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
        request_cost: int = 1,
    ) -> ProviderProbeResult:
        if self._config.mode == DataMode.FIXTURE.value:
            return _fallback_result(
                provider,
                payload={"mode": DataMode.FIXTURE.value},
                warning="FIXTURE_MODE_FORCES_OFFLINE_DATA",
            )
        runtime_cache_key = cache_key or f"probe:{provider}"
        runtime = self._provider_runtime
        runtime_store_warning: str | None = None
        if runtime is not None:
            try:
                cached = runtime.cache.get_valid(provider, runtime_cache_key)
                if cached is not None:
                    return ProviderProbeResult(
                        provider=provider,
                        data_mode=DataMode.FALLBACK.value,
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
                if not runtime.budget.try_consume(provider, cost=request_cost):
                    return _fallback_result(
                        provider,
                        payload={"requestBudget": self._request_budget},
                        warning=f"{provider.upper()}_BUDGET_EXHAUSTED",
                    )
                self._requests_used += request_cost
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
            if (
                runtime is None
                and self._requests_used + request_cost > self._request_budget
            ):
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
                self._requests_used += request_cost
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
                            error_code=(
                                result.warnings[0] if result.warnings else "ProviderFallback"
                            ),
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
                            request_cost=request_cost,
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
            if status_code == 401:
                warning = f"{provider.upper()}_AUTHENTICATION_FALLBACK_ACTIVE"
            elif status_code == 403:
                warning = f"{provider.upper()}_FORBIDDEN_FALLBACK_ACTIVE"
            elif status_code == 429:
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
            self._failed_provider_counts.get(provider, 0) >= self._circuit_breaker_failure_threshold
        )

    def _record_provider_failure(self, provider: str) -> None:
        self._failed_provider_counts[provider] = self._failed_provider_counts.get(provider, 0) + 1
