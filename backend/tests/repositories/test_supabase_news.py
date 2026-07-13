from __future__ import annotations

from datetime import UTC, datetime

from app.contracts.entities import AssetRelation, DataMode, Event, Freshness, allow_internal_field_names
from app.repositories.fixture_repository import FixtureRepository


def _event(event_id: str, *, data_mode: DataMode) -> Event:
    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    warnings = ("FIXTURE_DATA",) if data_mode == DataMode.FIXTURE else ()
    with allow_internal_field_names():
        return Event(
            id=event_id,
            title=f"Title {event_id}",
            summary="Summary",
            event_at=now,
            article_ids=("art_demo",),
            related_assets=(
                AssetRelation(
                    asset_id="ast_aapl",
                    symbol="AAPL",
                    relationship="direct",
                    reason="demo",
                    entity_match_score=0.9,
                ),
            ),
            created_at=now,
            updated_at=now,
            data_mode=data_mode,
            provider="gdelt" if data_mode == DataMode.LIVE else "fixture_news_feed",
            retrieved_at=now,
            data_as_of=now,
            freshness=Freshness(evaluated_at=now, stale_after_seconds=86400, is_stale=False),
            warnings=warnings,
        )


def test_list_events_prefers_non_fixture_when_available() -> None:
    repository = object.__new__(FixtureRepository)
    repository._lock = __import__("threading").RLock()
    repository._assets = {
        "ast_aapl": type("Asset", (), {"id": "ast_aapl", "instrument_type": type("IT", (), {"value": "equity"})()})()
    }
    repository._events = {
        "evt_fixture": _event("evt_fixture", data_mode=DataMode.FIXTURE),
        "evt_live": _event("evt_live", data_mode=DataMode.LIVE),
    }

    events = FixtureRepository.list_events(repository)

    assert len(events) == 1
    assert events[0][0].id == "evt_live"


def test_list_events_falls_back_to_fixture_when_no_live_events() -> None:
    repository = object.__new__(FixtureRepository)
    repository._lock = __import__("threading").RLock()
    repository._assets = {
        "ast_aapl": type("Asset", (), {"id": "ast_aapl", "instrument_type": type("IT", (), {"value": "equity"})()})()
    }
    repository._events = {
        "evt_fixture_a": _event("evt_fixture_a", data_mode=DataMode.FIXTURE),
        "evt_fixture_b": _event("evt_fixture_b", data_mode=DataMode.FIXTURE),
    }

    events = FixtureRepository.list_events(repository)

    assert len(events) == 2
    assert all(event.data_mode == DataMode.FIXTURE for event, _ in events)
