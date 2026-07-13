"""Market snapshot endpoints."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_instrument_service, get_market_service
from app.contracts.api import (
    InstrumentSearchResponse,
    MarketQuoteListResponse,
    MarketSnapshotListResponse,
)
from app.services.instrument_service import InstrumentService
from app.services.market_service import MarketService

router = APIRouter(tags=["market"])
InstrumentServiceDep = Annotated[InstrumentService, Depends(get_instrument_service)]
MarketServiceDep = Annotated[MarketService, Depends(get_market_service)]


@router.get(
    "/market-snapshots",
    response_model=MarketSnapshotListResponse,
    operation_id="listMarketSnapshots",
)
def list_market_snapshots(
    service: MarketServiceDep,
    asset: str | None = None,
    interval: Annotated[Literal["1h", "1d"] | None, Query()] = None,
) -> MarketSnapshotListResponse:
    return service.list_market_snapshots(asset=asset, interval=interval)


@router.get(
    "/instruments",
    response_model=InstrumentSearchResponse,
    operation_id="listInstruments",
)
def list_instruments(
    service: InstrumentServiceDep,
    query: Annotated[str | None, Query(min_length=2, max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
) -> InstrumentSearchResponse:
    return service.list_instruments(query=query, limit=limit)


@router.get(
    "/market-quotes",
    response_model=MarketQuoteListResponse,
    operation_id="listMarketQuotes",
)
def list_market_quotes(
    service: InstrumentServiceDep,
    symbols: Annotated[str, Query(min_length=1, max_length=256)],
) -> MarketQuoteListResponse:
    try:
        normalized = service.normalize_symbols(symbols)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return service.list_quotes(normalized)
