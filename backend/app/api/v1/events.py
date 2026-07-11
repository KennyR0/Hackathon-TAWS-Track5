"""Event endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_event_service
from app.contracts.api import EventListResponse, EventResponse, WatchlistResponse
from app.services.event_service import EventService

router = APIRouter(tags=["events"])


@router.get("/events", response_model=EventListResponse, operation_id="listEvents")
def list_events(
    instrument_type: Annotated[str | None, Query(alias="instrumentType")] = None,
    asset: str | None = None,
    published_after: Annotated[str | None, Query(alias="publishedAfter")] = None,
    service: EventService = Depends(get_event_service),
) -> EventListResponse:
    return service.list_events(
        instrument_type=instrument_type,
        asset=asset,
        published_after=published_after,
    )


@router.get("/events/{event_id}", response_model=EventResponse, operation_id="getEvent")
def get_event(
    event_id: str,
    service: EventService = Depends(get_event_service),
) -> EventResponse:
    return service.get_event(event_id)


@router.get(
    "/watchlists/demo-global",
    response_model=WatchlistResponse,
    operation_id="getDemoWatchlist",
)
def get_demo_watchlist(
    service: EventService = Depends(get_event_service),
) -> WatchlistResponse:
    return service.get_watchlist()
