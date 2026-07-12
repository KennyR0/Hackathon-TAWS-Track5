from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import DEFAULT_MARKET_DATA_MODE, MarketProviderConfig, get_market_provider_config, get_runtime_config
from app.contracts.entities import DataMode
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService, _live_result
from app.repositories.fixture_repository import FixtureRepository

REPO_ROOT = Path(__file__).resolve().parents[3]


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


class _FailingPriceProvider:
    def __init__(self) -> None:
        self.calls = 0

    def probe(self, symbol: str):
        self.calls += 1
        raise TimeoutError(f"{symbol} timed out")


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
    assert snapshot.requests_used == 5
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
    assert first_snapshot.data_mode == DataMode.FALLBACK
    assert first_snapshot.checks["aapl"].warnings == ("TWELVE_DATA_FALLBACK_ACTIVE",)
    assert second_snapshot.checks["aapl"].warnings == ("TWELVE_DATA_CIRCUIT_OPEN",)


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
    assert snapshot.checks["btc"].warnings == ("COINGECKO_BUDGET_EXHAUSTED",)


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
