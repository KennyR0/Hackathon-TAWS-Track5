"""Provider circuit breaker health persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from supabase import Client


@dataclass(frozen=True)
class ProviderHealthState:
    provider: str
    circuit_state: str
    consecutive_failures: int
    opened_at: datetime | None = None
    retry_after: datetime | None = None


class ProviderHealthRepository(Protocol):
    def is_circuit_open(self, provider: str) -> bool: ...

    def record_success(self, provider: str) -> None: ...

    def record_failure(self, provider: str, *, error_code: str | None = None) -> None: ...


class InMemoryProviderHealthRepository:
    def __init__(self, *, failure_threshold: int = 1, retry_seconds: int = 60) -> None:
        self._failure_threshold = failure_threshold
        self._retry_seconds = retry_seconds
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, datetime] = {}

    def is_circuit_open(self, provider: str) -> bool:
        opened = self._opened_at.get(provider)
        if opened is None:
            return self._failures.get(provider, 0) >= self._failure_threshold
        elapsed = datetime.now(UTC) - opened
        if elapsed >= timedelta(seconds=self._retry_seconds):
            return False
        return True

    def record_success(self, provider: str) -> None:
        self._failures.pop(provider, None)
        self._opened_at.pop(provider, None)

    def record_failure(self, provider: str, *, error_code: str | None = None) -> None:
        count = self._failures.get(provider, 0) + 1
        self._failures[provider] = count
        if count >= self._failure_threshold:
            self._opened_at[provider] = datetime.now(UTC)


class SupabaseProviderHealthRepository:
    def __init__(
        self,
        client: Client,
        *,
        failure_threshold: int = 1,
        retry_seconds: int = 60,
    ) -> None:
        self._client = client
        self._failure_threshold = failure_threshold
        self._retry_seconds = retry_seconds

    def _get_row(self, provider: str) -> dict | None:
        rows = (
            self._client.table("provider_health")
            .select("*")
            .eq("provider", provider)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def _ensure_row(self, provider: str) -> None:
        if self._get_row(provider) is None:
            now = datetime.now(UTC).isoformat()
            self._client.table("provider_health").insert(
                {
                    "provider": provider,
                    "circuit_state": "closed",
                    "consecutive_failures": 0,
                    "updated_at": now,
                }
            ).execute()

    def is_circuit_open(self, provider: str) -> bool:
        self._ensure_row(provider)
        row = self._get_row(provider)
        if row is None:
            return False
        state = row["circuit_state"]
        now = datetime.now(UTC)
        if state == "open":
            retry_after = row.get("retry_after")
            if retry_after and retry_after <= now.isoformat():
                self._client.table("provider_health").update(
                    {
                        "circuit_state": "half_open",
                        "updated_at": now.isoformat(),
                    }
                ).eq("provider", provider).execute()
                return False
            return True
        if state == "half_open":
            return False
        return row["consecutive_failures"] >= self._failure_threshold

    def record_success(self, provider: str) -> None:
        self._ensure_row(provider)
        now = datetime.now(UTC).isoformat()
        self._client.table("provider_health").update(
            {
                "circuit_state": "closed",
                "consecutive_failures": 0,
                "opened_at": None,
                "retry_after": None,
                "last_success_at": now,
                "last_error_code": None,
                "last_error_message": None,
                "updated_at": now,
            }
        ).eq("provider", provider).execute()

    def record_failure(self, provider: str, *, error_code: str | None = None) -> None:
        self._ensure_row(provider)
        row = self._get_row(provider)
        failures = (row["consecutive_failures"] if row else 0) + 1
        now = datetime.now(UTC)
        updates: dict[str, object] = {
            "consecutive_failures": failures,
            "last_failure_at": now.isoformat(),
            "last_error_code": error_code,
            "updated_at": now.isoformat(),
        }
        if failures >= self._failure_threshold:
            updates["circuit_state"] = "open"
            updates["opened_at"] = now.isoformat()
            updates["retry_after"] = (now + timedelta(seconds=self._retry_seconds)).isoformat()
        self._client.table("provider_health").update(updates).eq("provider", provider).execute()


__all__ = [
    "InMemoryProviderHealthRepository",
    "ProviderHealthRepository",
    "ProviderHealthState",
    "SupabaseProviderHealthRepository",
]
