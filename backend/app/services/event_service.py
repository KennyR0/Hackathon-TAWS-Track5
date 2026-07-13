"""Event query services."""

from __future__ import annotations

from app.contracts.api import EventListResponse, EventResponse, EventView, WatchlistResponse
from app.contracts.entities import allow_internal_field_names
from app.repositories.fixture_repository import FixtureRepository


class EventService:
    def __init__(self, repository: FixtureRepository) -> None:
        self._repository = repository

    def list_events(
        self,
        *,
        instrument_type: str | None = None,
        asset: str | None = None,
        published_after: str | None = None,
    ) -> EventListResponse:
        data = tuple(
            self._build_event_view(event.id)
            for event, _ in self._repository.list_events(
                instrument_type=instrument_type,
                asset=asset,
                published_after=published_after,
            )
        )
        get_event_meta = getattr(self._repository, "get_event_meta", None)
        meta = get_event_meta() if callable(get_event_meta) else self._repository.get_meta()
        with allow_internal_field_names():
            return EventListResponse(data=data, meta=meta)

    def get_event(self, event_id: str) -> EventResponse:
        self._repository.get_event(event_id)
        get_event_meta = getattr(self._repository, "get_event_meta", None)
        meta = get_event_meta() if callable(get_event_meta) else self._repository.get_meta()
        with allow_internal_field_names():
            return EventResponse(
                data=self._build_event_view(event_id),
                meta=meta,
            )

    def get_watchlist(self) -> WatchlistResponse:
        with allow_internal_field_names():
            return WatchlistResponse(
                data=self._repository.get_watchlist(),
                meta=self._repository.get_meta(),
            )

    def _build_event_view(self, event_id: str) -> EventView:
        event, _ = self._repository.get_event(event_id)
        with allow_internal_field_names():
            return EventView(
                event=event,
                articles=self._repository.get_event_articles(event_id),
                sources=self._repository.get_event_sources(event_id),
            )
