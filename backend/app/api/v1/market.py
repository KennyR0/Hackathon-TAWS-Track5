"""Market snapshot endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_market_service
from app.contracts.api import MarketSnapshotListResponse
from app.services.market_service import MarketService

router = APIRouter(tags=["market"])


@router.get(
    "/market-snapshots",
    response_model=MarketSnapshotListResponse,
    operation_id="listMarketSnapshots",
)
def list_market_snapshots(
    asset: str | None = None,
    interval: Annotated[Literal["1h", "1d"] | None, Query()] = None,
    service: MarketService = Depends(get_market_service),
) -> MarketSnapshotListResponse:
    return service.list_market_snapshots(asset=asset, interval=interval)
