"""Provider cache adapters for runtime fallback reuse."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock
from typing import Any

from supabase import Client

from app.contracts.fixtures import canonical_json_bytes, sha256_digest
from app.providers.base import CachedProviderProbe, ProviderCacheStore, ProviderProbeResult


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _serialize_probe(entry: CachedProviderProbe) -> dict[str, Any]:
    return {
        "provider": entry.probe.provider,
        "dataMode": entry.probe.data_mode,
        "ok": entry.probe.ok,
        "warnings": list(entry.probe.warnings),
        "payload": entry.probe.payload,
    }


def _deserialize_probe(cache_key: str, row: dict[str, Any]) -> CachedProviderProbe:
    payload = row.get("payload") or {}
    probe_payload = payload.get("payload") or {}
    probe = ProviderProbeResult(
        provider=payload["provider"],
        data_mode=payload["dataMode"],
        ok=payload["ok"],
        warnings=tuple(payload.get("warnings") or ()),
        payload=probe_payload,
    )
    return CachedProviderProbe(
        cache_key=cache_key,
        provider=row["provider"],
        resource_type=row["resource_type"],
        probe=probe,
        retrieved_at=datetime.fromisoformat(row["retrieved_at"]),
        data_as_of=datetime.fromisoformat(row["data_as_of"]),
        expires_at=datetime.fromisoformat(row["expires_at"]),
    )


class InMemoryProviderCacheStore(ProviderCacheStore):
    def __init__(self) -> None:
        self._entries: dict[str, CachedProviderProbe] = {}
        self._lock = RLock()

    def read(self, cache_key: str) -> CachedProviderProbe | None:
        with self._lock:
            entry = self._entries.get(cache_key)
            if entry is None:
                return None
            if entry.expires_at <= _utc_now():
                self._entries.pop(cache_key, None)
                return None
            return entry

    def write(self, entry: CachedProviderProbe) -> None:
        with self._lock:
            self._entries[entry.cache_key] = entry


class SupabaseProviderCacheStore(ProviderCacheStore):
    def __init__(self, client: Client) -> None:
        self._client = client

    def read(self, cache_key: str) -> CachedProviderProbe | None:
        rows = (
            self._client.table("provider_cache")
            .select("*")
            .eq("cache_key", cache_key)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        entry = _deserialize_probe(cache_key, rows[0])
        if entry.expires_at <= _utc_now():
            return None
        return entry

    def write(self, entry: CachedProviderProbe) -> None:
        payload = _serialize_probe(entry)
        payload_bytes = canonical_json_bytes(payload)
        self._client.table("provider_cache").upsert(
            {
                "cache_key": entry.cache_key,
                "provider": entry.provider,
                "resource_type": entry.resource_type,
                "payload": payload,
                "content_hash": sha256_digest(payload_bytes),
                "data_mode": entry.probe.data_mode,
                "retrieved_at": entry.retrieved_at.isoformat(),
                "data_as_of": entry.data_as_of.isoformat(),
                "expires_at": entry.expires_at.isoformat(),
            }
        ).execute()


__all__ = [
    "InMemoryProviderCacheStore",
    "SupabaseProviderCacheStore",
]
