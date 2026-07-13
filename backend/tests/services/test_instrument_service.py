from __future__ import annotations

import pytest

from app.market_universe import load_market_universe
from app.providers.base import ProviderProbeResult
from app.services.instrument_service import INSTRUMENT_ALIASES, InstrumentService


class QuoteRuntimeStub:
    def collect_quotes(self, instruments) -> dict[str, ProviderProbeResult]:
        return {
            item.symbol: ProviderProbeResult(
                provider="quote_stub",
                data_mode="live",
                ok=True,
                warnings=(),
                payload={"close": 100, "previousClose": 98},
            )
            for item in instruments
        }


def _service() -> InstrumentService:
    return InstrumentService(load_market_universe(), QuoteRuntimeStub())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("content", "expected_symbol"),
    [
        ("Explícame Apple", "AAPL"),
        ("¿Qué pasa con bitcoin?", "BTC-USD"),
        ("Analiza BTC", "BTC-USD"),
        ("Contexto de Ethereum", "ETH-USD"),
        ("Precio del petróleo", "WTI"),
        ("Perspectiva del crudo", "WTI"),
        ("Compara Google", "GOOGL"),
        ("Resume Coca-Cola", "KO"),
        ("Háblame de JP Morgan", "JPM"),
    ],
)
def test_resolve_mention_handles_names_aliases_and_accents(
    content: str,
    expected_symbol: str,
) -> None:
    match = _service().resolve_mention(content)
    assert match is not None
    assert match.symbol == expected_symbol


def test_resolve_mention_covers_every_versioned_instrument() -> None:
    service = _service()
    for instrument in service.instruments:
        by_symbol = service.resolve_mention(f"Analiza {instrument.symbol.lower()} ahora")
        by_name = service.resolve_mention(f"Explica {instrument.name.upper()}")
        assert by_symbol is not None and by_symbol.symbol == instrument.symbol
        assert by_name is not None and by_name.symbol == instrument.symbol


def test_every_versioned_instrument_has_a_stable_alias_entry() -> None:
    service = _service()
    assert {item.symbol for item in service.instruments} == set(INSTRUMENT_ALIASES)


def test_alias_matching_respects_word_boundaries_and_longest_match() -> None:
    service = _service()
    assert service.resolve_mention("El costo operativo aumentó") is None
    assert service.resolve_mention("Analiza META Platforms").symbol == "META"  # type: ignore[union-attr]


def test_detect_unsupported_uppercase_symbol() -> None:
    service = _service()
    assert service.detect_unsupported_symbol("Explica SOL con datos") == "SOL"
    assert service.detect_unsupported_symbol("EXPLICA AAPL HOY") is None

