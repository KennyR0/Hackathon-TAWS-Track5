"""In-memory and Supabase-backed provider cache persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Protocol

from supabase import Client


@dataclass(frozen=True)
class ProviderCacheEntry:
    cache_key: str
    provider: str
    request_params_hash: str
    response_json: dict[str, Any]
    fetched_at: datetime
    expires_at: datetime
    request_cost: int
    status_code: int
    data_mode: str
    content_hash: str | None = None


class ProviderCacheRepository(Protocol):
    def get_valid(self, provider: str, cache_key: str) -> ProviderCacheEntry | None: ...

    def put(self, entry: ProviderCacheEntry) -> None: ...


class InMemoryProviderCacheRepository:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], ProviderCacheEntry] = {}

    def get_valid(self, provider: str, cache_key: str) -> ProviderCacheEntry | None:
        entry = self._entries.get((provider, cache_key))
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            return None
        return entry

    def put(self, entry: ProviderCacheEntry) -> None:
        self._entries[(entry.provider, entry.cache_key)] = entry


class SupabaseProviderCacheRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def get_valid(self, provider: str, cache_key: str) -> ProviderCacheEntry | None:
        rows = (
            self._client.table("provider_cache")
            .select("*")
            .eq("provider", provider)
            .eq("cache_key", cache_key)
            .gt("expires_at", datetime.now(UTC).isoformat())
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        row = rows[0]
        return ProviderCacheEntry(
            cache_key=row["cache_key"],
            provider=row["provider"],
            request_params_hash=row["request_params_hash"],
            response_json=row["response_json"],
            fetched_at=row["fetched_at"],
            expires_at=row["expires_at"],
            request_cost=row["request_cost"],
            status_code=row["status_code"],
            data_mode=row["data_mode"],
            content_hash=row.get("content_hash"),
        )

    def put(self, entry: ProviderCacheEntry) -> None:
        self._client.table("provider_cache").upsert(
            {
                "cache_key": entry.cache_key,
                "provider": entry.provider,
                "request_params_hash": entry.request_params_hash,
                "response_json": entry.response_json,
                "fetched_at": entry.fetched_at.isoformat(),
                "expires_at": entry.expires_at.isoformat(),
                "request_cost": entry.request_cost,
                "status_code": entry.status_code,
                "data_mode": entry.data_mode,
                "content_hash": entry.content_hash,
            },
            on_conflict="provider,cache_key",
        ).execute()


def params_hash(payload: dict[str, Any]) -> str:
    canonical = str(sorted(payload.items())).encode()
    return f"sha256:{sha256(canonical).hexdigest()}"


__all__ = [
    "InMemoryProviderCacheRepository",
    "ProviderCacheEntry",
    "ProviderCacheRepository",
    "SupabaseProviderCacheRepository",
    "params_hash",
]
