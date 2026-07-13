"""Production universe search and auditable quote assembly."""

from __future__ import annotations

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


__all__ = ["InstrumentService"]
