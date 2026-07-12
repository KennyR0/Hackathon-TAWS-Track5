"""Provider request budget persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from supabase import Client


@dataclass(frozen=True)
class ProviderBudget:
    provider: str
    period_type: str
    max_requests: int
    used_requests: int
    safety_reserve: int
    reset_at: datetime


class ProviderBudgetRepository(Protocol):
    def try_consume(self, provider: str, *, cost: int = 1) -> bool: ...

    def requests_used(self, provider: str) -> int: ...


class InMemoryProviderBudgetRepository:
    def __init__(self, *, max_requests: int, safety_reserve: int = 0) -> None:
        self._max_requests = max_requests
        self._safety_reserve = safety_reserve
        self._used: dict[str, int] = {}

    def try_consume(self, provider: str, *, cost: int = 1) -> bool:
        used = self._used.get(provider, 0)
        limit = self._max_requests - self._safety_reserve
        if used + cost > limit:
            return False
        self._used[provider] = used + cost
        return True

    def requests_used(self, provider: str) -> int:
        return self._used.get(provider, 0)


class SupabaseProviderBudgetRepository:
    def __init__(
        self,
        client: Client,
        *,
        period_type: str = "hour",
        max_requests: int,
        safety_reserve: int = 0,
    ) -> None:
        self._client = client
        self._period_type = period_type
        self._max_requests = max_requests
        self._safety_reserve = safety_reserve

    def _ensure_row(self, provider: str) -> None:
        now = datetime.now(UTC)
        reset_at = now + timedelta(hours=1)
        self._client.table("provider_budgets").upsert(
            {
                "provider": provider,
                "period_type": self._period_type,
                "max_requests": self._max_requests,
                "used_requests": 0,
                "safety_reserve": self._safety_reserve,
                "reset_at": reset_at.isoformat(),
                "updated_at": now.isoformat(),
            },
            on_conflict="provider,period_type",
        ).execute()

    def try_consume(self, provider: str, *, cost: int = 1) -> bool:
        self._ensure_row(provider)
        rows = (
            self._client.table("provider_budgets")
            .select("*")
            .eq("provider", provider)
            .eq("period_type", self._period_type)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return False
        row = rows[0]
        now = datetime.now(UTC)
        if row["reset_at"] and row["reset_at"] < now.isoformat():
            self._client.table("provider_budgets").update(
                {
                    "used_requests": 0,
                    "reset_at": (now + timedelta(hours=1)).isoformat(),
                    "updated_at": now.isoformat(),
                }
            ).eq("provider", provider).eq("period_type", self._period_type).execute()
            used = 0
            max_requests = row["max_requests"]
            safety_reserve = row["safety_reserve"]
        else:
            used = row["used_requests"]
            max_requests = row["max_requests"]
            safety_reserve = row["safety_reserve"]
        limit = max_requests - safety_reserve
        if used + cost > limit:
            return False
        self._client.table("provider_budgets").update(
            {
                "used_requests": used + cost,
                "updated_at": now.isoformat(),
            }
        ).eq("provider", provider).eq("period_type", self._period_type).execute()
        return True

    def requests_used(self, provider: str) -> int:
        rows = (
            self._client.table("provider_budgets")
            .select("used_requests")
            .eq("provider", provider)
            .eq("period_type", self._period_type)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0]["used_requests"] if rows else 0


__all__ = [
    "InMemoryProviderBudgetRepository",
    "ProviderBudget",
    "ProviderBudgetRepository",
    "SupabaseProviderBudgetRepository",
]
