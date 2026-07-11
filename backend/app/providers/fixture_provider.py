"""Local fixture data provider."""

from __future__ import annotations

from pathlib import Path

from app.contracts.fixtures import FixtureBundle, load_fixture_bundle
from app.providers.base import FixtureDataProvider


class FixtureProvider(FixtureDataProvider):
    """Load the canonical Phase 0 fixture bundle from disk."""

    def __init__(self, bundle_path: Path) -> None:
        self._bundle_path = bundle_path
        self._cached_bundle: FixtureBundle | None = None

    def load_bundle(self) -> FixtureBundle:
        if self._cached_bundle is None:
            self._cached_bundle = load_fixture_bundle(self._bundle_path)
        return self._cached_bundle
