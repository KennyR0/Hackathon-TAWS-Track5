from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.config import (
    DEFAULT_MARKET_DATA_MODE,
    MarketProviderConfig,
    ProviderBudgetPolicy,
    get_market_provider_config,
    get_runtime_config,
)
from app.contracts.entities import DataMode
from app.market_universe import load_market_universe
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import (
    EIAMacroProvider,
    GDELTNewsProvider,
    MarketDataRuntimeService,
    RapidAPIYHFinanceProvider,
    _live_result,
)
from app.providers.provider_cache import InMemoryProviderCacheStore
from app.repositories.fixture_repository import FixtureRepository
from app.services.provider_runtime_service import build_in_memory_provider_runtime

REPO_ROOT = Path(__file__).resolve().parents[3]


class _StubFixtureProvider:
    def load_bundle(self):
        raise LookupError("fixture bundle unavailable for this isolated provider test")


class _NewsProvider:
    def probe(self):
        return _live_result("gdelt", {"articleCount": 2})


class _FinnhubNewsProvider:
    def probe(self):
        return _live_result("finnhub_news", {"articleCount": 3, "query": "AAPL"})


class _PriceProvider:
    def probe(self, symbol: str):
        return _live_result("price", {"symbol": symbol, "value": 123.4})


class _BatchPriceProvider(_PriceProvider):
    def probe_many(self, symbols: tuple[str, ...]):
        return _live_result(
            "twelve_data",
            {"quotes": {symbol: {"symbol": symbol, "close": "123.4"} for symbol in symbols}},
        )


class _CountingPriceProvider(_PriceProvider):
    def __init__(self) -> None:
        self.calls = 0

    def probe(self, symbol: str):
        self.calls += 1
        return super().probe(symbol)


class _MacroProvider:
    def probe(self, series_id: str):
        return _live_result("fred", {"seriesId": series_id, "value": "78.1"})


class _CountingMacroProvider(_MacroProvider):
    def __init__(self) -> None:
        self.calls = 0

    def probe(self, series_id: str):
        self.calls += 1
        return super().probe(series_id)


class _TimeoutMacroProvider:
    def probe(self, series_id: str):
        raise httpx.TimeoutException(f"{series_id} timeout")


class _FailingPriceProvider:
    def __init__(self) -> None:
        self.calls = 0

    def probe(self, symbol: str):
        self.calls += 1
        raise TimeoutError(f"{symbol} timed out")


class _FailingRuntimeCache:
    def get_valid(self, provider: str, cache_key: str):
        raise RuntimeError(f"{provider}:{cache_key}: durable cache unavailable")

    def put(self, entry) -> None:
        raise RuntimeError("durable cache unavailable")


def test_runtime_config_uses_fixture_market_mode_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MARKET_DATA_MODE", raising=False)

    config = get_runtime_config()

    assert config.market_data_mode == DEFAULT_MARKET_DATA_MODE


def test_runtime_config_rejects_invalid_market_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKET_DATA_MODE", "turbo")

    with pytest.raises(RuntimeError, match="MARKET_DATA_MODE must be one of"):
        get_runtime_config()


def test_market_provider_config_reads_optional_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MARKET_DATA_MODE", "hybrid")
    monkeypatch.setenv("FINNHUB_API_KEY", "fh-key")
    monkeypatch.setenv("FINNHUB_API_KEY_2", "fh-key-2")
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "td-key")
    monkeypatch.setenv("TWELVE_DATA_API_KEY_2", "td-key-2")
    monkeypatch.setenv("COINGECKO_API_KEY", "cg-key")
    monkeypatch.setenv("COINGECKO_API_KEY_2", "cg-key-2")
    monkeypatch.setenv("FRED_API_KEY", "fred-key")
    monkeypatch.setenv("FRED_API_KEY_2", "fred-key-2")
    monkeypatch.setenv("GDELT_BASE_URL", "https://example.test/gdelt")
    monkeypatch.setenv("SEC_USER_AGENT", "NexoMercadoAI test@example.com")
    monkeypatch.setenv("GDELT_TIMEOUT_SECONDS", "4.5")
    monkeypatch.setenv("GDELT_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("GDELT_CACHE_TTL_SECONDS", "600")
    monkeypatch.setenv("EIA_API_KEY", "eia-key")
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-key")
    monkeypatch.setenv("YAHOO_FINANCE_API_HOST", "yahoo-finance15.p.rapidapi.com")
    monkeypatch.setenv(
        "YAHOO_FINANCE_BASE_URL",
        "https://yahoo-finance15.p.rapidapi.com",
    )
    monkeypatch.setenv(
        "MARKET_PROVIDER_BUDGETS",
        '{"twelve_data":{"period":"day","maxRequests":800,"safetyReserve":40}}',
    )

    config = get_market_provider_config()

    assert config.mode == "hybrid"
    assert config.finnhub_api_key == "fh-key"
    assert config.finnhub_api_keys == ("fh-key", "fh-key-2")
    assert config.twelve_data_api_key == "td-key"
    assert config.twelve_data_api_keys == ("td-key", "td-key-2")
    assert config.coingecko_api_keys == ("cg-key", "cg-key-2")
    assert config.gdelt_base_url == "https://example.test/gdelt"
    assert config.gdelt_user_agent == "NexoMercadoAI test@example.com"
    assert config.gdelt_timeout_seconds == 4.5
    assert config.gdelt_max_attempts == 3
    assert config.gdelt_cache_ttl_seconds == 600
    assert config.fred_api_key == "fred-key"
    assert config.fred_api_keys == ("fred-key", "fred-key-2")
    assert config.eia_api_key == "eia-key"
    assert config.rapidapi_key == "rapid-key"
    assert config.yahoo_finance_api_host == "yahoo-finance15.p.rapidapi.com"
    assert config.yahoo_finance_history_path == "/api/v2/markets/stock/history"
    assert config.provider_budgets == {
        "twelve_data": ProviderBudgetPolicy(
            period="day",
            max_requests=800,
            safety_reserve=40,
        )
    }


@pytest.mark.parametrize(
    "payload, message",
    [
        ("not-json", "valid JSON"),
        ('{"unknown":{"period":"day","maxRequests":2}}', "unknown provider"),
        ('{"fred":{"period":"week","maxRequests":2}}', "must be one of"),
        ('{"fred":{"period":"day","maxRequests":2,"safetyReserve":2}}', "lower than"),
    ],
)
def test_market_provider_config_rejects_invalid_provider_budgets(
    monkeypatch: pytest.MonkeyPatch,
    payload: str,
    message: str,
) -> None:
    monkeypatch.setenv("MARKET_PROVIDER_BUDGETS", payload)

    with pytest.raises(RuntimeError, match=message):
        get_market_provider_config()


def test_market_provider_config_requires_complete_rapidapi_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rapid-key")

    with pytest.raises(RuntimeError, match="must be configured together"):
        get_market_provider_config()


@pytest.mark.parametrize(
    "provider",
    ["FINNHUB", "TWELVE_DATA", "COINGECKO", "FRED"],
)
def test_market_provider_config_rejects_secondary_key_without_primary(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    monkeypatch.setenv(f"{provider}_API_KEY_2", "secondary")

    with pytest.raises(RuntimeError, match="requires"):
        get_market_provider_config()


@pytest.mark.parametrize(
    "provider",
    ["FINNHUB", "TWELVE_DATA", "COINGECKO", "FRED"],
)
def test_market_provider_config_rejects_duplicate_keys(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    monkeypatch.setenv(f"{provider}_API_KEY", "same")
    monkeypatch.setenv(f"{provider}_API_KEY_2", "same")

    with pytest.raises(RuntimeError, match="must differ"):
        get_market_provider_config()


def test_repository_provenance_uses_fixture_mode() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="fixture"),
        _StubFixtureProvider(),
    )

    meta = service.repository_provenance(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))

    assert meta.data_mode == DataMode.FIXTURE
    assert meta.provider == "fixture_repository"


def test_repository_provenance_marks_fallback_when_live_mode_is_active() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
    )

    meta = service.repository_provenance(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))

    assert meta.data_mode == DataMode.FALLBACK
    assert "LIVE_MODE_ACTIVE_USING_FIXTURE_FALLBACK" in meta.warnings


def test_collect_demo_snapshot_reports_live_when_all_providers_succeed() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="live"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.LIVE
    assert snapshot.requests_used == 5
    assert snapshot.checks["news"].ok is True
    assert snapshot.checks["btc"].data_mode == DataMode.LIVE


def test_collect_demo_snapshot_marks_durable_cache_hits_without_new_requests() -> None:
    runtime = build_in_memory_provider_runtime(request_budget=8)
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        provider_runtime=runtime,
    )

    first = service.collect_demo_snapshot()
    second = service.collect_demo_snapshot()

    assert first.requests_used == 5
    assert second.requests_used == 0
    assert second.checks["aapl"].payload["servedFromCache"] is True
    assert second.checks["aapl"].payload["cacheFetchedAt"]
    assert second.checks["aapl"].warnings == ("TWELVE_DATA_CACHE_HIT",)


def test_collect_demo_snapshot_continues_when_durable_runtime_store_fails() -> None:
    runtime = build_in_memory_provider_runtime(request_budget=8)
    runtime = type(runtime)(
        cache=_FailingRuntimeCache(),
        budget=runtime.budget,
        health=runtime.health,
    )
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        provider_runtime=runtime,
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.LIVE
    assert snapshot.requests_used == 5
    assert snapshot.warnings == ("PROVIDER_RUNTIME_STORE_UNAVAILABLE",)
    assert snapshot.checks["news"].ok is True
    assert "PROVIDER_RUNTIME_STORE_UNAVAILABLE" in snapshot.checks["news"].warnings


def test_collect_demo_snapshot_falls_back_in_hybrid_without_keys() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.FALLBACK
    assert snapshot.checks["aapl"].ok is False
    assert "TWELVE_DATA_KEY_MISSING" in snapshot.checks["aapl"].warnings


def test_collect_demo_snapshot_retries_and_opens_circuit_after_provider_error() -> None:
    failing_provider = _FailingPriceProvider()
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="live"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=failing_provider,
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        retry_limit=1,
    )

    first_snapshot = service.collect_demo_snapshot()
    second_snapshot = service.collect_demo_snapshot()

    assert failing_provider.calls == 2
    assert first_snapshot.data_mode == DataMode.LIVE
    assert first_snapshot.checks["aapl"].provider == "price"
    assert "TWELVE_DATA_TO_FINNHUB_FAILOVER" in first_snapshot.checks["aapl"].warnings
    assert "TWELVE_DATA_CIRCUIT_OPEN" in second_snapshot.checks["aapl"].warnings


def test_collect_demo_snapshot_respects_request_budget() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="live"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        request_budget=2,
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.FALLBACK
    assert snapshot.requests_used == 2
    assert snapshot.checks["spy"].warnings == ("FINNHUB_BUDGET_EXHAUSTED",)
    assert "COINGECKO_BUDGET_EXHAUSTED" in snapshot.checks["btc"].warnings
    assert "RAPIDAPI_YH_FINANCE_BUDGET_EXHAUSTED" in snapshot.checks["btc"].warnings
    assert "COINGECKO_TO_RAPIDAPI_YH_FINANCE_FAILOVER" in snapshot.checks["btc"].warnings


def test_twelve_data_batch_consumes_one_budget_credit_per_symbol() -> None:
    runtime = build_in_memory_provider_runtime(request_budget=2)
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="live"),
        _StubFixtureProvider(),
        equity_price_provider=_BatchPriceProvider(),
        metadata_provider=_PriceProvider(),
        provider_runtime=runtime,
    )
    equities = load_market_universe().instruments[:2]

    results = service.collect_quotes(equities)

    assert all(result.ok for result in results.values())
    assert service._requests_used == 2
    assert runtime.budget.requests_used("twelve_data") == 2


class _RetryingGDELTClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, *_args, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            raise httpx.TimeoutException("timeout")
        request = httpx.Request("GET", "https://example.test/gdelt")
        return httpx.Response(
            200,
            request=request,
            json={"articles": [{"title": "Apple extends gains"}]},
        )


def test_gdelt_provider_retries_timeout_and_succeeds() -> None:
    client = _RetryingGDELTClient()
    provider = GDELTNewsProvider(
        base_url="https://example.test/gdelt",
        user_agent="NexoMercadoAI test@example.com",
        timeout_seconds=2.0,
        max_attempts=2,
        client=client,
        sleep_fn=lambda _seconds: None,
    )

    result = provider.probe()

    assert result.ok is True
    assert result.provider == "gdelt"
    assert result.payload["articleCount"] == 1
    assert client.calls == 2


class _RateLimitedNewsProvider:
    def probe(self):
        request = httpx.Request("GET", "https://example.test/gdelt")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)


def test_collect_demo_snapshot_classifies_gdelt_rate_limit_fallback() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_RateLimitedNewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.FALLBACK
    assert snapshot.checks["news"].ok is False
    assert "GDELT_RATE_LIMIT_FALLBACK_ACTIVE" in snapshot.checks["news"].warnings
    assert snapshot.checks["news"].payload["statusCode"] == 429


def test_collect_demo_snapshot_fails_over_from_gdelt_to_finnhub_news() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_TimeoutNewsProvider(),
        news_fallback_provider=_FinnhubNewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.LIVE
    assert snapshot.checks["news"].provider == "finnhub_news"
    assert snapshot.checks["news"].payload["articleCount"] == 3
    assert "GDELT_TO_FINNHUB_FAILOVER" in snapshot.checks["news"].warnings


class _TimeoutNewsProvider:
    def probe(self):
        raise httpx.TimeoutException("timeout")


class _TimeoutPriceProvider:
    def probe(self, symbol: str):
        raise httpx.TimeoutException(f"{symbol} timeout")

    def probe_many(self, symbols: tuple[str, ...]):
        raise httpx.TimeoutException(f"{','.join(symbols)} timeout")


class _HTTPStatusPriceProvider:
    def __init__(self, status_code: int) -> None:
        self._status_code = status_code

    def probe(self, symbol: str):
        request = httpx.Request("GET", "https://yahoo-finance15.p.rapidapi.com")
        response = httpx.Response(self._status_code, request=request)
        raise httpx.HTTPStatusError(
            f"YH Finance failed for {symbol}",
            request=request,
            response=response,
        )


def test_twelve_data_rotates_to_secondary_key_before_finnhub() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        equity_price_providers=(_TimeoutPriceProvider(), _BatchPriceProvider()),
        metadata_provider=_PriceProvider(),
        retry_limit=0,
    )

    instruments = load_market_universe().instruments[:2]
    results = service.collect_quotes(instruments)

    assert all(result.provider == "twelve_data" for result in results.values())
    assert all(
        "TWELVE_DATA_KEY_1_TO_KEY_2_FAILOVER" in result.warnings
        for result in results.values()
    )
    assert all(
        "TWELVE_DATA_TO_FINNHUB_FAILOVER" not in result.warnings
        for result in results.values()
    )


def test_coingecko_rotates_to_secondary_key_with_independent_runtime_state() -> None:
    runtime = build_in_memory_provider_runtime(request_budget=5)
    yahoo = _CountingPriceProvider()
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        crypto_price_providers=(_TimeoutPriceProvider(), _PriceProvider()),
        crypto_fallback_provider=yahoo,
        provider_runtime=runtime,
        retry_limit=0,
    )

    result = service._probe_crypto("BTC-USD")

    assert result.ok is True
    assert result.provider == "price"
    assert "COINGECKO_KEY_1_TO_KEY_2_FAILOVER" in result.warnings
    assert "COINGECKO_TO_RAPIDAPI_YH_FINANCE_FAILOVER" not in result.warnings
    assert yahoo.calls == 0
    assert runtime.budget.requests_used("coingecko_key_1") == 1
    assert runtime.budget.requests_used("coingecko_key_2") == 1
    assert runtime.health.is_circuit_open("coingecko_key_1") is True
    assert runtime.health.is_circuit_open("coingecko_key_2") is False


def test_fred_rotates_to_secondary_key_before_eia() -> None:
    eia = _CountingMacroProvider()
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        macro_providers=(_TimeoutMacroProvider(), _MacroProvider()),
        macro_fallback_provider=eia,
        retry_limit=0,
    )

    result = service._probe_macro("DCOILWTICO")

    assert result.ok is True
    assert result.provider == "fred"
    assert "FRED_KEY_1_TO_KEY_2_FAILOVER" in result.warnings
    assert "FRED_TO_EIA_FAILOVER" not in result.warnings
    assert eia.calls == 0


def test_finnhub_news_rotates_to_secondary_key_before_fixture() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_TimeoutNewsProvider(),
        news_fallback_providers=(_TimeoutNewsProvider(), _FinnhubNewsProvider()),
        retry_limit=0,
    )

    result = service._probe_news()

    assert result.ok is True
    assert result.provider == "finnhub_news"
    assert "FINNHUB_KEY_1_TO_KEY_2_FAILOVER" in result.warnings
    assert "GDELT_TO_FINNHUB_FAILOVER" in result.warnings
    assert "FIXTURE_NEWS_FALLBACK_ACTIVE" not in result.warnings


class _RapidAPIYHFinanceClient:
    def __init__(self, payload: dict[str, object] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.payload = payload or {
            "providerPayload": {
                "opaque": True,
                "records": [{"field": "uninterpreted"}],
            }
        }

    def get(self, *_args, **_kwargs):
        self.calls.append(_kwargs)
        request = httpx.Request(
            "GET",
            "https://yahoo-finance15.p.rapidapi.com/api/v2/markets/stock/history",
        )
        return httpx.Response(
            200,
            request=request,
            json=self.payload,
        )


class _EIAClient:
    def get(self, *_args, **_kwargs):
        request = httpx.Request("GET", "https://api.eia.gov/v2/petroleum/pri/spt/data/")
        return httpx.Response(
            200,
            request=request,
            json={
                "response": {
                    "data": [{"series": "RWTC", "period": "2026-07-10", "value": "77.12"}]
                }
            },
        )


def test_rapidapi_yh_finance_returns_raw_json_without_schema_assumptions() -> None:
    client = _RapidAPIYHFinanceClient()
    result = RapidAPIYHFinanceProvider(
        api_key="rapid-key",
        api_host="yahoo-finance15.p.rapidapi.com",
        base_url="https://yahoo-finance15.p.rapidapi.com",
        client=client,
    ).probe_many(("BTC-USD", "ETH-USD"))

    assert result.ok is True
    assert result.provider == "rapidapi_yh_finance"
    assert result.payload["quotes"]["BTC-USD"]["rawResponse"] == {
        "providerPayload": {
            "opaque": True,
            "records": [{"field": "uninterpreted"}],
        }
    }
    assert client.calls[0]["headers"]["X-RapidAPI-Key"] == "rapid-key"
    assert client.calls[0]["headers"]["X-RapidAPI-Host"] == (
        "yahoo-finance15.p.rapidapi.com"
    )
    assert client.calls[0]["params"] == {
        "symbol": "BTC-USD",
        "interval": "1d",
        "limit": 30,
    }


def test_rapidapi_yh_finance_preserves_no_data_json_and_activates_fallback() -> None:
    result = RapidAPIYHFinanceProvider(
        api_key="rapid-key",
        api_host="yahoo-finance15.p.rapidapi.com",
        base_url="https://yahoo-finance15.p.rapidapi.com",
        client=_RapidAPIYHFinanceClient(
            {"success": False, "message": "No data returned"}
        ),
    ).probe("BTC-USD")

    assert result.ok is False
    assert result.data_mode == DataMode.FALLBACK
    assert result.payload["rawResponse"] == {
        "success": False,
        "message": "No data returned",
    }
    assert result.warnings == ("RAPIDAPI_YH_FINANCE_NO_DATA_FALLBACK_ACTIVE",)


def test_eia_provider_normalizes_wti_observation() -> None:
    result = EIAMacroProvider("eia-key", client=_EIAClient()).probe("DCOILWTICO")

    assert result.ok is True
    assert result.provider == "eia"
    assert result.payload == {"seriesId": "RWTC", "value": "77.12", "date": "2026-07-10"}


def test_crypto_failover_uses_rapidapi_yh_finance_and_preserves_primary_warning() -> None:
    fallback = _CountingPriceProvider()
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        crypto_price_provider=_TimeoutPriceProvider(),
        crypto_fallback_provider=fallback,
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        macro_fallback_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
    )

    snapshot = service.collect_demo_snapshot()

    assert fallback.calls == 1
    assert snapshot.checks["btc"].provider == "price"
    assert "COINGECKO_TIMEOUT_FALLBACK_ACTIVE" in snapshot.checks["btc"].warnings
    assert "COINGECKO_TO_RAPIDAPI_YH_FINANCE_FAILOVER" in snapshot.checks["btc"].warnings


@pytest.mark.parametrize(
    "status_code, warning",
    [
        (401, "RAPIDAPI_YH_FINANCE_AUTHENTICATION_FALLBACK_ACTIVE"),
        (403, "RAPIDAPI_YH_FINANCE_FORBIDDEN_FALLBACK_ACTIVE"),
        (429, "RAPIDAPI_YH_FINANCE_RATE_LIMIT_FALLBACK_ACTIVE"),
    ],
)
def test_yh_finance_http_errors_fall_back_to_fixture(
    status_code: int,
    warning: str,
) -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        fixture_provider,
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_TimeoutPriceProvider(),
        crypto_fallback_provider=_HTTPStatusPriceProvider(status_code),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        retry_limit=0,
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.checks["btc"].provider == "fixture_market"
    assert snapshot.checks["btc"].data_mode == DataMode.FALLBACK
    assert warning in snapshot.checks["btc"].warnings
    assert "FIXTURE_QUOTE_FALLBACK_ACTIVE" in snapshot.checks["btc"].warnings


def test_yh_finance_timeout_falls_back_to_fixture() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        fixture_provider,
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_TimeoutPriceProvider(),
        crypto_fallback_provider=_TimeoutPriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        retry_limit=0,
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.checks["btc"].provider == "fixture_market"
    assert "RAPIDAPI_YH_FINANCE_TIMEOUT_FALLBACK_ACTIVE" in snapshot.checks["btc"].warnings


def test_macro_failover_uses_eia_and_skips_it_when_fred_succeeds() -> None:
    fallback = _CountingPriceProvider()
    failed_service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        crypto_fallback_provider=_PriceProvider(),
        macro_provider=_TimeoutPriceProvider(),
        macro_fallback_provider=fallback,
        metadata_provider=_PriceProvider(),
    )
    failed_snapshot = failed_service.collect_demo_snapshot()

    assert fallback.calls == 1
    assert "FRED_TO_EIA_FAILOVER" in failed_snapshot.checks["wti"].warnings

    unused_fallback = _CountingPriceProvider()
    successful_service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        crypto_fallback_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        macro_fallback_provider=unused_fallback,
        metadata_provider=_PriceProvider(),
    )
    successful_service.collect_demo_snapshot()

    assert unused_fallback.calls == 0


def test_failed_provider_chains_return_traceable_fixture_quotes() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        fixture_provider,
        equity_price_provider=_TimeoutPriceProvider(),
        metadata_provider=_TimeoutPriceProvider(),
        crypto_price_provider=_TimeoutPriceProvider(),
        crypto_fallback_provider=_TimeoutPriceProvider(),
        macro_provider=_TimeoutPriceProvider(),
        macro_fallback_provider=_TimeoutPriceProvider(),
        retry_limit=0,
    )
    by_symbol = {item.symbol: item for item in load_market_universe().instruments}

    results = service.collect_quotes(
        (by_symbol["AAPL"], by_symbol["BTC-USD"], by_symbol["WTI"])
    )

    assert {result.provider for result in results.values()} == {"fixture_market"}
    assert all(result.data_mode == DataMode.FALLBACK for result in results.values())
    assert all(result.payload["close"] > 0 for result in results.values())
    assert all("FIXTURE_QUOTE_FALLBACK_ACTIVE" in result.warnings for result in results.values())


def test_failed_news_chain_returns_fixture_articles() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        fixture_provider,
        news_provider=_TimeoutNewsProvider(),
        news_fallback_provider=None,
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        retry_limit=0,
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.checks["news"].provider == "fixture_news"
    assert snapshot.checks["news"].payload["articleCount"] > 0
    assert "FIXTURE_NEWS_FALLBACK_ACTIVE" in snapshot.checks["news"].warnings


def test_collect_demo_snapshot_uses_cached_gdelt_payload_on_timeout() -> None:
    cache_store = InMemoryProviderCacheStore()
    warm_service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid", gdelt_cache_ttl_seconds=900),
        _StubFixtureProvider(),
        news_provider=_NewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        provider_cache=cache_store,
    )
    warm_snapshot = warm_service.collect_demo_snapshot()
    assert warm_snapshot.checks["news"].ok is True

    cold_service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid", gdelt_cache_ttl_seconds=900),
        _StubFixtureProvider(),
        news_provider=_TimeoutNewsProvider(),
        equity_price_provider=_PriceProvider(),
        crypto_price_provider=_PriceProvider(),
        macro_provider=_MacroProvider(),
        metadata_provider=_PriceProvider(),
        provider_cache=cache_store,
    )

    snapshot = cold_service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.FALLBACK
    assert snapshot.checks["news"].ok is False
    assert "GDELT_TIMEOUT_FALLBACK_ACTIVE" in snapshot.checks["news"].warnings
    assert "GDELT_CACHED_FALLBACK_ACTIVE" in snapshot.checks["news"].warnings
    assert snapshot.checks["news"].payload["servedFromCache"] is True
    assert snapshot.checks["news"].payload["articleCount"] == 2


def test_repository_fallback_mode_reduces_signal_confidence() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    fixture_repository = FixtureRepository(
        fixture_provider,
        market_runtime=MarketDataRuntimeService(
            MarketProviderConfig(mode="fixture"),
            fixture_provider,
        ),
    )
    fallback_repository = FixtureRepository(
        fixture_provider,
        market_runtime=MarketDataRuntimeService(
            MarketProviderConfig(mode="hybrid"),
            fixture_provider,
        ),
    )

    fixture_signal = fixture_repository.build_runtime_signal("sig_aapl_negative")
    fallback_signal = fallback_repository.build_runtime_signal("sig_aapl_negative")

    assert fallback_repository.get_meta().data_mode == DataMode.FALLBACK
    assert fallback_signal.confidence == pytest.approx(fixture_signal.confidence - 0.10)
