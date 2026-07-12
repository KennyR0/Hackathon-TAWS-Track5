"""Provider interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


@dataclass(frozen=True)
class CachedProviderProbe:
    cache_key: str
    provider: str
    resource_type: str
    probe: ProviderProbeResult
    retrieved_at: datetime
    data_as_of: datetime
    expires_at: datetime


class NewsProvider(Protocol):
    def probe(self) -> ProviderProbeResult: ...


class PriceProvider(Protocol):
    def probe(self, symbol: str) -> ProviderProbeResult: ...


class MacroProvider(Protocol):
    def probe(self, series_id: str) -> ProviderProbeResult: ...


class ProviderCacheStore(Protocol):
    def read(self, cache_key: str) -> CachedProviderProbe | None: ...

    def write(self, entry: CachedProviderProbe) -> None: ...
