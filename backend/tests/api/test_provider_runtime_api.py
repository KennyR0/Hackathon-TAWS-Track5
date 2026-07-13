from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.dependencies import get_provider_demo_service
from app.main import create_app
from app.providers.base import ProviderProbeResult
from app.providers.live_market import MarketRuntimeSnapshot
from app.services.provider_demo_service import ProviderDemoService


class StubMarketRuntime:
    mode = "hybrid"

    def collect_demo_snapshot(self) -> MarketRuntimeSnapshot:
        return MarketRuntimeSnapshot(
            data_mode="fallback",
            provider="gdelt+twelve_data+finnhub+coingecko+fred",
            warnings=("GDELT_TIMEOUT_FALLBACK_ACTIVE", "FRED_BUDGET_EXHAUSTED"),
            request_budget=8,
            requests_used=6,
            checks={
                "news": ProviderProbeResult(
                    provider="gdelt",
                    data_mode="fallback",
                    ok=False,
                    warnings=("GDELT_TIMEOUT_FALLBACK_ACTIVE",),
                    payload={
                        "error": "TimeoutException",
                        "attempts": 2,
                        "retryable": True,
                        "apiKey": "never-serialize-this",
                    },
                ),
                "aapl": ProviderProbeResult(
                    provider="twelve_data",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"symbol": "AAPL", "close": "315.32", "currency": "USD"},
                ),
                "spy": ProviderProbeResult(
                    provider="finnhub",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"symbol": "SPY", "current": 754.95, "previousClose": 751.71},
                ),
                "btc": ProviderProbeResult(
                    provider="coingecko",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"symbol": "BTC-USD", "usd": 64057, "lastUpdatedAt": "invalid"},
                ),
                "wti": ProviderProbeResult(
                    provider="fred",
                    data_mode="fallback",
                    ok=False,
                    warnings=("FRED_BUDGET_EXHAUSTED",),
                    payload={"requestBudget": 8, "requestsUsed": 8, "attempts": 0},
                ),
            },
        )


class ExplodingMarketRuntime:
    mode = "hybrid"

    def collect_demo_snapshot(self) -> MarketRuntimeSnapshot:
        raise RuntimeError("provider_health table is missing")


class FailoverNewsRuntime:
    mode = "hybrid"

    def collect_demo_snapshot(self) -> MarketRuntimeSnapshot:
        return MarketRuntimeSnapshot(
            data_mode="live",
            provider="finnhub_news+twelve_data+finnhub+coingecko+fred",
            warnings=("GDELT_TO_FINNHUB_FAILOVER",),
            request_budget=8,
            requests_used=5,
            checks={
                "news": ProviderProbeResult(
                    provider="finnhub_news",
                    data_mode="live",
                    ok=True,
                    warnings=("GDELT_TO_FINNHUB_FAILOVER",),
                    payload={"articleCount": 3, "query": "AAPL"},
                ),
                "aapl": ProviderProbeResult(
                    provider="twelve_data",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"symbol": "AAPL", "close": "315.32", "currency": "USD"},
                ),
                "spy": ProviderProbeResult(
                    provider="finnhub",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"symbol": "SPY", "current": 754.95, "previousClose": 751.71},
                ),
                "btc": ProviderProbeResult(
                    provider="coingecko",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"symbol": "BTC-USD", "usd": 64057},
                ),
                "wti": ProviderProbeResult(
                    provider="fred",
                    data_mode="live",
                    ok=True,
                    warnings=(),
                    payload={"seriesId": "DCOILWTICO", "value": "78.1", "date": "2026-07-10"},
                ),
            },
        )


def test_runtime_provider_endpoint_exposes_hybrid_status_without_secrets() -> None:
    app = create_app()
    service = ProviderDemoService(StubMarketRuntime())  # type: ignore[arg-type]
    app.dependency_overrides[get_provider_demo_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/runtime/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["configuredMode"] == "hybrid"
    assert payload["data"]["effectiveDataMode"] == "fallback"
    assert payload["data"]["requestBudget"] == 8
    assert payload["data"]["requestsUsed"] == 6
    assert len(payload["data"]["checks"]) == 5
    assert [item["key"] for item in payload["data"]["checks"]] == [
        "news",
        "aapl",
        "spy",
        "btc",
        "wti",
    ]
    aapl = next(item for item in payload["data"]["checks"] if item["key"] == "aapl")
    news = next(item for item in payload["data"]["checks"] if item["key"] == "news")
    btc = next(item for item in payload["data"]["checks"] if item["key"] == "btc")
    assert aapl["dataMode"] == "live"
    assert aapl["metrics"]["close"] == "315.32"
    assert news["warnings"] == ["GDELT_TIMEOUT_FALLBACK_ACTIVE"]
    assert "apiKey" not in news["metrics"]
    assert "never-serialize-this" not in response.text
    assert btc["dataAsOf"] is None


def test_runtime_provider_endpoint_falls_back_when_runtime_store_fails() -> None:
    app = create_app()
    service = ProviderDemoService(ExplodingMarketRuntime())  # type: ignore[arg-type]
    app.dependency_overrides[get_provider_demo_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/runtime/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["effectiveDataMode"] == "fallback"
    assert "PROVIDER_RUNTIME_STORE_UNAVAILABLE" in payload["data"]["warnings"]
    assert len(payload["data"]["checks"]) == 5
    assert all(check["dataMode"] == "fallback" for check in payload["data"]["checks"])
    assert "provider_health table is missing" not in response.text


def test_runtime_provider_endpoint_canonicalizes_news_failover_provider() -> None:
    app = create_app()
    service = ProviderDemoService(FailoverNewsRuntime())  # type: ignore[arg-type]
    app.dependency_overrides[get_provider_demo_service] = lambda: service

    with TestClient(app) as client:
        response = client.get("/api/v1/runtime/providers")

    assert response.status_code == 200
    payload = response.json()
    news = next(item for item in payload["data"]["checks"] if item["key"] == "news")
    assert news["provider"] == "gdelt"
    assert news["warnings"] == ["GDELT_TO_FINNHUB_FAILOVER"]
