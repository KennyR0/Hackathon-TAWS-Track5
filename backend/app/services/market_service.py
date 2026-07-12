"""Market snapshot query services."""

from __future__ import annotations

from app.contracts.api import MarketSnapshotListResponse
from app.contracts.entities import allow_internal_field_names
from app.repositories.fixture_repository import FixtureRepository


class MarketService:
    def __init__(self, repository: FixtureRepository) -> None:
        self._repository = repository

    def list_market_snapshots(
        self,
        *,
        asset: str | None = None,
        interval: str | None = None,
    ) -> MarketSnapshotListResponse:
        with allow_internal_field_names():
            return MarketSnapshotListResponse(
                data=self._repository.list_market_snapshots(asset=asset, interval=interval),
                meta=self._repository.get_meta(),
            )
