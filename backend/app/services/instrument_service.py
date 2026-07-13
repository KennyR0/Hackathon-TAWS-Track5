"""Production universe search and auditable quote assembly."""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime

from app.contracts.api import (
    InstrumentSearchResponse,
    InstrumentSummary,
    MarketQuote,
    MarketQuoteListResponse,
)
from app.contracts.entities import DataMode, DataProvenance, Freshness, allow_internal_field_names
from app.market_universe import MarketUniverse, UniverseInstrument
from app.providers.live_market import MarketDataRuntimeService

INSTRUMENT_ALIASES: dict[str, tuple[str, ...]] = {
    "AAPL": ("apple",),
    "MSFT": ("microsoft",),
    "NVDA": ("nvidia",),
    "AMZN": ("amazon",),
    "GOOGL": ("alphabet", "google"),
    "META": ("meta platforms", "facebook"),
    "TSLA": ("tesla",),
    "JPM": ("jpmorgan", "jp morgan"),
    "BAC": ("bank of america",),
    "V": ("visa",),
    "WMT": ("walmart",),
    "COST": ("costco",),
    "XOM": ("exxon", "exxon mobil"),
    "CVX": ("chevron",),
    "UNH": ("unitedhealth", "united health"),
    "JNJ": ("johnson & johnson", "johnson and johnson"),
    "PFE": ("pfizer",),
    "KO": ("coca-cola", "coca cola"),
    "DIS": ("disney", "walt disney"),
    "NFLX": ("netflix",),
    "SPY": ("spdr s&p 500", "s&p 500 etf"),
    "QQQ": ("invesco qqq",),
    "BTC-USD": ("bitcoin", "btc", "btcusd"),
    "ETH-USD": ("ethereum", "eth", "ethusd"),
    "WTI": (
        "west texas intermediate",
        "petroleo",
        "petróleo",
        "crudo",
    ),
}

_UNSUPPORTED_SYMBOL_STOPWORDS = frozenset(
    {
        "ANALIZA",
        "COMO",
        "CON",
        "CUAL",
        "CUALES",
        "DAME",
        "DEL",
        "DESDE",
        "EL",
        "EN",
        "ES",
        "ESTA",
        "ESTE",
        "EXPLICA",
        "HOY",
        "LA",
        "LAS",
        "LOS",
        "PARA",
        "POR",
        "QUE",
        "RESUME",
        "SENAL",
        "SEÑAL",
        "UNA",
    }
)


def _normalize_mention(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


def _contains_alias(normalized_content: str, normalized_alias: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])"
    return re.search(pattern, normalized_content) is not None


def _freshness(now: datetime, *, stale: bool = False) -> Freshness:
    with allow_internal_field_names():
        return Freshness(
            evaluated_at=now,
            stale_after_seconds=300,
            is_stale=stale,
        )


def _summary(instrument: UniverseInstrument) -> InstrumentSummary:
    with allow_internal_field_names():
        return InstrumentSummary(
            id=instrument.id,
            symbol=instrument.symbol,
            name=instrument.name,
            instrument_type=instrument.instrument_type,
            currency=instrument.currency,
            exchange=instrument.exchange,
            benchmark_symbol=instrument.benchmark_symbol,
            series_id=instrument.series_id,
        )


def _number(value: object) -> float | None:
    if isinstance(value, (int, float, str)):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
    return None


class InstrumentService:
    def __init__(
        self,
        universe: MarketUniverse,
        market_runtime: MarketDataRuntimeService,
    ) -> None:
        self._universe = universe
        self._market_runtime = market_runtime
        self._by_symbol = {item.symbol: item for item in universe.instruments}
        aliases: list[tuple[str, UniverseInstrument]] = []
        for instrument in universe.instruments:
            candidates = {
                instrument.symbol,
                instrument.symbol.replace("-", ""),
                instrument.name,
                *INSTRUMENT_ALIASES.get(instrument.symbol, ()),
            }
            aliases.extend(
                (_normalize_mention(alias), instrument)
                for alias in candidates
                if _normalize_mention(alias)
            )
        self._mention_aliases = tuple(
            sorted(set(aliases), key=lambda item: len(item[0]), reverse=True)
        )

    @property
    def instruments(self) -> tuple[UniverseInstrument, ...]:
        return self._universe.instruments

    def get_instrument(self, symbol: str | None) -> UniverseInstrument | None:
        if not symbol:
            return None
        return self._by_symbol.get(symbol.upper())

    def resolve_mention(self, content: str) -> UniverseInstrument | None:
        normalized_content = _normalize_mention(content)
        return next(
            (
                instrument
                for alias, instrument in self._mention_aliases
                if _contains_alias(normalized_content, alias)
            ),
            None,
        )

    def detect_unsupported_symbol(self, content: str) -> str | None:
        for match in re.finditer(
            r"(?<![A-Za-z0-9])\$?([A-Z][A-Z0-9]{1,5}(?:-[A-Z]{3})?)(?![A-Za-z0-9])",
            content,
        ):
            symbol = match.group(1)
            if symbol in self._by_symbol or symbol in _UNSUPPORTED_SYMBOL_STOPWORDS:
                continue
            return symbol
        return None

    def list_instruments(self, *, query: str | None, limit: int) -> InstrumentSearchResponse:
        normalized = (query or "").strip().casefold()
        instruments = self._universe.instruments
        if normalized:
            instruments = tuple(
                item
                for item in instruments
                if normalized in item.symbol.casefold() or normalized in item.name.casefold()
            )
        now = datetime.now(UTC)
        with allow_internal_field_names():
            meta = DataProvenance(
                data_mode=DataMode.FIXTURE,
                provider=f"production_universe_v{self._universe.version}",
                retrieved_at=now,
                data_as_of=now,
                freshness=_freshness(now),
                warnings=("VERSIONED_UNIVERSE_CATALOG",),
            )
            selected = instruments[:limit] if normalized else instruments
            return InstrumentSearchResponse(
                data=tuple(_summary(item) for item in selected),
                meta=meta,
            )

    def list_quotes(self, symbols: tuple[str, ...]) -> MarketQuoteListResponse:
        instruments = tuple(self._by_symbol[symbol] for symbol in symbols)
        results = self._market_runtime.collect_quotes(instruments)
        now = datetime.now(UTC)
        quotes: list[MarketQuote] = []
        all_warnings: list[str] = []
        for instrument in instruments:
            result = results[instrument.symbol]
            payload = result.payload
            price = _number(
                payload.get("close")
                or payload.get("current")
                or payload.get("usd")
                or payload.get("value")
            )
            previous_close = _number(payload.get("previousClose"))
            change_percent = None
            if price is not None and previous_close is not None:
                change_percent = (price - previous_close) / previous_close
            warnings = result.warnings or (() if result.ok else ("QUOTE_UNAVAILABLE",))
            all_warnings.extend(warnings)
            with allow_internal_field_names():
                quotes.append(
                    MarketQuote(
                        symbol=instrument.symbol,
                        name=instrument.name,
                        instrument_type=instrument.instrument_type,
                        currency=instrument.currency,
                        price=price,
                        previous_close=previous_close,
                        change_percent=change_percent,
                        data_mode=DataMode(result.data_mode),
                        provider=result.provider,
                        retrieved_at=now,
                        data_as_of=now,
                        freshness=_freshness(now),
                        warnings=warnings,
                    )
                )
        effective_mode = (
            DataMode.LIVE
            if quotes and all(item.data_mode == DataMode.LIVE for item in quotes)
            else DataMode.FALLBACK
        )
        meta_warnings = tuple(dict.fromkeys(all_warnings))
        if effective_mode == DataMode.FALLBACK and not meta_warnings:
            meta_warnings = ("PARTIAL_QUOTE_FALLBACK",)
        with allow_internal_field_names():
            meta = DataProvenance(
                data_mode=effective_mode,
                provider="market_universe_runtime",
                retrieved_at=now,
                data_as_of=now,
                freshness=_freshness(now),
                warnings=meta_warnings,
            )
            return MarketQuoteListResponse(data=tuple(quotes), meta=meta)

    def normalize_symbols(self, raw_symbols: str) -> tuple[str, ...]:
        symbols = tuple(
            dict.fromkeys(item.strip().upper() for item in raw_symbols.split(",") if item.strip())
        )
        if not symbols:
            raise ValueError("At least one symbol is required")
        if len(symbols) > 10:
            raise ValueError("At most 10 symbols can be quoted per request")
        unknown = [symbol for symbol in symbols if symbol not in self._by_symbol]
        if unknown:
            raise ValueError(f"Unsupported market universe symbols: {', '.join(unknown)}")
        return symbols


__all__ = ["INSTRUMENT_ALIASES", "InstrumentService"]
