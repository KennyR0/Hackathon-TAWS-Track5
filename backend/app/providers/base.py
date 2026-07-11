"""Provider interfaces."""

from __future__ import annotations

from typing import Protocol

from app.contracts.fixtures import FixtureBundle


class FixtureDataProvider(Protocol):
    """Provider capable of loading the offline fixture bundle."""

    def load_bundle(self) -> FixtureBundle: ...
