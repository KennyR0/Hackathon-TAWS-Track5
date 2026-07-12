"""Provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.contracts.fixtures import FixtureBundle


class FixtureDataProvider(Protocol):
    """Provider capable of loading the offline fixture bundle."""

    def load_bundle(self) -> FixtureBundle: ...


@dataclass(frozen=True)
class ProviderProbeResult:
    provider: str
    data_mode: str
    ok: bool
    warnings: tuple[str, ...]
    payload: dict[str, object]


class NewsProvider(Protocol):
    def probe(self) -> ProviderProbeResult: ...


class PriceProvider(Protocol):
    def probe(self, symbol: str) -> ProviderProbeResult: ...


class MacroProvider(Protocol):
    def probe(self, series_id: str) -> ProviderProbeResult: ...
