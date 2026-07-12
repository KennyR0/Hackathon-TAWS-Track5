"""Live provider adapters and runtime fallback orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.config import MarketProviderConfig
from app.contracts.entities import DataMode, DataProvenance, Freshness, allow_internal_field_names
from app.providers.base import FixtureDataProvider, MacroProvider, NewsProvider, PriceProvider, ProviderProbeResult

FIXTURE_WARNINGS: tuple[str, ...] = ("FIXTURE_DATA", "NOT_REAL_TIME")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _fallback_result(
    provider: str,
    *,
    payload: dict[str, object],
    warning: str,
) -> ProviderProbeResult:
    return ProviderProbeResult(
        provider=provider,
        data_mode=DataMode.FALLBACK.value,
        ok=False,
        warnings=(warning,),
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


class GDELTNewsProvider(NewsProvider):
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=10.0)

    def probe(self) -> ProviderProbeResult:
        response = self._client.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": '"Apple" OR Bitcoin OR crude',
                "mode": "ArtList",
                "maxrecords": 3,
                "format": "json",
            },
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return _live_result(
            "gdelt",
            {"articleCount": len(articles), "titles": [item.get("title") for item in articles[:3]]},
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
            {"symbol": symbol, "usd": payload.get("usd"), "lastUpdatedAt": payload.get("last_updated_at")},
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
    ) -> None:
        self._config = config
        self._fixture_provider = fixture_provider
        self._news_provider = news_provider or GDELTNewsProvider()
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

        for key, provider_call in (
            ("news", lambda: self._safe_probe(self._news_provider.probe, "gdelt")),
            ("aapl", lambda: self._safe_probe(lambda: self._equity_price_provider.probe("AAPL"), "twelve_data")),
            ("spy", lambda: self._safe_probe(lambda: self._metadata_provider.probe("SPY"), "finnhub")),
            ("btc", lambda: self._safe_probe(lambda: self._crypto_price_provider.probe("BTC-USD"), "coingecko")),
            ("wti", lambda: self._safe_probe(lambda: self._macro_provider.probe("DCOILWTICO"), "fred")),
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
        )

    def _safe_probe(self, probe, provider: str) -> ProviderProbeResult:
        if self._config.mode == DataMode.FIXTURE.value:
            return _fallback_result(
                provider,
                payload={"mode": DataMode.FIXTURE.value},
                warning="FIXTURE_MODE_FORCES_OFFLINE_DATA",
            )
        try:
            return probe()
        except Exception as exc:
            return _fallback_result(
                provider,
                payload={"error": type(exc).__name__},
                warning=f"{provider.upper()}_FALLBACK_ACTIVE",
            )
