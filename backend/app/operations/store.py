"""Persistence boundary for idempotent worker tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from supabase import Client

from app.contracts.fixtures import FixtureBundle


class OperationStore(Protocol):
    def ingest(self, bundle: FixtureBundle) -> tuple[int, int]: ...
    def market(self, bundle: FixtureBundle, *, macro: bool) -> tuple[int, int]: ...
    def reconcile(self, bundle: FixtureBundle) -> tuple[int, int]: ...
    def cleanup(self, now: datetime) -> tuple[int, int]: ...


@dataclass
class InMemoryOperationStore:
    records: dict[str, set[str]] = field(default_factory=dict)

    def _upsert(self, table: str, ids: set[str]) -> tuple[int, int]:
        current = self.records.setdefault(table, set())
        before = len(current)
        current.update(ids)
        return len(ids), len(current) - before

    def ingest(self, bundle: FixtureBundle) -> tuple[int, int]:
        raw = self._upsert(
            "raw_source_snapshots",
            {item.id for item in bundle.raw_source_snapshots},
        )
        articles = self._upsert("articles", {item.id for item in bundle.articles})
        return raw[0] + articles[0], raw[1] + articles[1]

    def market(self, bundle: FixtureBundle, *, macro: bool) -> tuple[int, int]:
        snapshots = {
            item.id
            for item in bundle.market_snapshots
            if (item.series_id is not None) is macro
        }
        return self._upsert("market_snapshots", snapshots)

    def reconcile(self, bundle: FixtureBundle) -> tuple[int, int]:
        links = {
            f"{event.id}:{article_id}"
            for event in bundle.events
            for article_id in event.article_ids
        }
        return self._upsert("event_articles", links)

    def cleanup(self, now: datetime) -> tuple[int, int]:
        _ = now
        expired = self.records.pop("expired", set())
        return len(expired), len(expired)


class SupabaseOperationStore:
    def __init__(self, client: Client) -> None:
        self._client = client

    @staticmethod
    def _json_row(model, *, exclude: set[str] | None = None) -> dict[str, object]:
        return model.model_dump(mode="json", by_alias=False, exclude=exclude or set())

    def ingest(self, bundle: FixtureBundle) -> tuple[int, int]:
        raw_rows = [self._json_row(item) for item in bundle.raw_source_snapshots]
        article_rows = [self._json_row(item) for item in bundle.articles]
        if raw_rows:
            self._client.table("raw_source_snapshots").upsert(raw_rows).execute()
        if article_rows:
            self._client.table("articles").upsert(article_rows).execute()
        total = len(raw_rows) + len(article_rows)
        return total, total

    def market(self, bundle: FixtureBundle, *, macro: bool) -> tuple[int, int]:
        snapshots = [
            item
            for item in bundle.market_snapshots
            if (item.series_id is not None) is macro
        ]
        snapshot_rows = [self._json_row(item, exclude={"observations"}) for item in snapshots]
        observation_rows = [
            {
                "market_snapshot_id": snapshot.id,
                "observed_at": point.timestamp.isoformat(),
                "close_value": point.close,
                "volume": point.volume,
                "open_value": point.open,
                "high_value": point.high,
                "low_value": point.low,
            }
            for snapshot in snapshots
            for point in snapshot.observations
        ]
        if snapshot_rows:
            self._client.table("market_snapshots").upsert(snapshot_rows).execute()
        if observation_rows:
            self._client.table("market_observations").upsert(
                observation_rows,
                on_conflict="market_snapshot_id,observed_at",
            ).execute()
        total = len(snapshot_rows) + len(observation_rows)
        return total, total

    def reconcile(self, bundle: FixtureBundle) -> tuple[int, int]:
        rows = [
            {"event_id": event.id, "article_id": article_id, "is_primary": index == 0}
            for event in bundle.events
            for index, article_id in enumerate(event.article_ids)
        ]
        if rows:
            self._client.table("event_articles").upsert(
                rows,
                on_conflict="event_id,article_id",
            ).execute()
        return len(rows), len(rows)

    def cleanup(self, now: datetime) -> tuple[int, int]:
        timestamp = now.astimezone(UTC).isoformat()
        idempotency = (
            self._client.table("idempotency_keys")
            .delete()
            .lt("expires_at", timestamp)
            .execute()
        )
        cache = self._client.table("provider_cache").delete().lt("expires_at", timestamp).execute()
        deleted = len(idempotency.data or []) + len(cache.data or [])
        return deleted, deleted


__all__ = ["InMemoryOperationStore", "OperationStore", "SupabaseOperationStore"]
