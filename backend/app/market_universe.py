"""Versioned production market universe."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.config import REPO_ROOT
from app.contracts.entities import InstrumentType

DEFAULT_UNIVERSE_PATH = REPO_ROOT / "data" / "universe" / "v1" / "production_universe.json"


class UniverseInstrument(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )

    id: str
    symbol: str
    name: str
    instrument_type: InstrumentType
    currency: str
    exchange: str
    benchmark_symbol: str | None = None
    series_id: str | None = None


class MarketUniverse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: int = Field(ge=1)
    instruments: tuple[UniverseInstrument, ...] = Field(min_length=25)


@lru_cache
def load_market_universe(path: Path = DEFAULT_UNIVERSE_PATH) -> MarketUniverse:
    universe = MarketUniverse.model_validate_json(path.read_text(encoding="utf-8"))
    symbols = [item.symbol for item in universe.instruments]
    identifiers = [item.id for item in universe.instruments]
    if len(symbols) != len(set(symbols)) or len(identifiers) != len(set(identifiers)):
        raise ValueError("Market universe symbols and ids must be unique")
    return universe


__all__ = ["MarketUniverse", "UniverseInstrument", "load_market_universe"]
