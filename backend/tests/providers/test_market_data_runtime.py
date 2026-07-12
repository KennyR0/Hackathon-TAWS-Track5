from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.config import DEFAULT_MARKET_DATA_MODE, MarketProviderConfig, get_market_provider_config, get_runtime_config
from app.contracts.entities import DataMode
from app.providers.live_market import MarketDataRuntimeService, _live_result


class _StubFixtureProvider:
    def load_bundle(self):
        raise AssertionError("fixture bundle should not be loaded for runtime probes")


class _NewsProvider:
    def probe(self):
        return _live_result("gdelt", {"articleCount": 2})


class _PriceProvider:
    def probe(self, symbol: str):
        return _live_result("price", {"symbol": symbol, "value": 123.4})


class _MacroProvider:
    def probe(self, series_id: str):
        return _live_result("fred", {"seriesId": series_id, "value": "78.1"})


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
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "td-key")

    config = get_market_provider_config()

    assert config.mode == "hybrid"
    assert config.finnhub_api_key == "fh-key"
    assert config.twelve_data_api_key == "td-key"
    assert config.fred_api_key is None


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
    assert snapshot.checks["news"].ok is True
    assert snapshot.checks["btc"].data_mode == DataMode.LIVE


def test_collect_demo_snapshot_falls_back_in_hybrid_without_keys() -> None:
    service = MarketDataRuntimeService(
        MarketProviderConfig(mode="hybrid"),
        _StubFixtureProvider(),
    )

    snapshot = service.collect_demo_snapshot()

    assert snapshot.data_mode == DataMode.FALLBACK
    assert snapshot.checks["aapl"].ok is False
    assert "TWELVE_DATA_KEY_MISSING" in snapshot.checks["aapl"].warnings
