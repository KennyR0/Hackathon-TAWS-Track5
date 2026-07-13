"""Provider request budget persistence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from supabase import Client

from app.config import ProviderBudgetPolicy


def _base_provider_name(provider: str) -> str:
    prefix, separator, suffix = provider.rpartition("_key_")
    return prefix if separator and suffix.isdigit() else provider


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


def _next_reset(now: datetime, period: str) -> datetime:
    if period == "minute":
        return now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if period == "hour":
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    if period == "month":
        if now.month == 12:
            return now.replace(
                year=now.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        return now.replace(
            month=now.month + 1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
    raise ValueError(f"Unsupported provider budget period: {period}")


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class InMemoryProviderBudgetRepository:
    def __init__(
        self,
        *,
        max_requests: int,
        safety_reserve: int = 0,
        period_type: str = "hour",
        provider_policies: Mapping[str, ProviderBudgetPolicy] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._default_policy = ProviderBudgetPolicy(
            period=period_type,
            max_requests=max_requests,
            safety_reserve=safety_reserve,
        )
        self._provider_policies = dict(provider_policies or {})
        self._clock = clock or (lambda: datetime.now(UTC))
        self._used: dict[tuple[str, str], int] = {}
        self._reset_at: dict[tuple[str, str], datetime] = {}

    def _policy(self, provider: str) -> ProviderBudgetPolicy:
        return self._provider_policies.get(
            provider,
            self._provider_policies.get(_base_provider_name(provider), self._default_policy),
        )

    def _current_usage(self, provider: str) -> tuple[ProviderBudgetPolicy, tuple[str, str], int]:
        policy = self._policy(provider)
        key = (provider, policy.period)
        now = self._clock()
        reset_at = self._reset_at.get(key)
        if reset_at is None or reset_at <= now:
            self._used[key] = 0
            self._reset_at[key] = _next_reset(now, policy.period)
        return policy, key, self._used.get(key, 0)

    def try_consume(self, provider: str, *, cost: int = 1) -> bool:
        if cost < 1:
            raise ValueError("Provider request cost must be >= 1")
        policy, key, used = self._current_usage(provider)
        limit = policy.max_requests - policy.safety_reserve
        if used + cost > limit:
            return False
        self._used[key] = used + cost
        return True

    def requests_used(self, provider: str) -> int:
        _, _, used = self._current_usage(provider)
        return used


class SupabaseProviderBudgetRepository:
    def __init__(
        self,
        client: Client,
        *,
        period_type: str = "hour",
        max_requests: int,
        safety_reserve: int = 0,
        provider_policies: Mapping[str, ProviderBudgetPolicy] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._default_policy = ProviderBudgetPolicy(
            period=period_type,
            max_requests=max_requests,
            safety_reserve=safety_reserve,
        )
        self._provider_policies = dict(provider_policies or {})
        self._clock = clock or (lambda: datetime.now(UTC))

    def _policy(self, provider: str) -> ProviderBudgetPolicy:
        return self._provider_policies.get(
            provider,
            self._provider_policies.get(_base_provider_name(provider), self._default_policy),
        )

    def _select_rows(self, provider: str, period: str, columns: str = "*") -> list[dict]:
        return (
            self._client.table("provider_budgets")
            .select(columns)
            .eq("provider", provider)
            .eq("period_type", period)
            .limit(1)
            .execute()
            .data
            or []
        )

    def _get_or_create_row(
        self,
        provider: str,
        policy: ProviderBudgetPolicy,
        now: datetime,
    ) -> dict | None:
        rows = self._select_rows(provider, policy.period)
        if rows:
            row = rows[0]
            if (
                row.get("max_requests") != policy.max_requests
                or row.get("safety_reserve") != policy.safety_reserve
            ):
                self._client.table("provider_budgets").update(
                    {
                        "max_requests": policy.max_requests,
                        "safety_reserve": policy.safety_reserve,
                        "updated_at": now.isoformat(),
                    }
                ).eq("provider", provider).eq("period_type", policy.period).execute()
                row = {
                    **row,
                    "max_requests": policy.max_requests,
                    "safety_reserve": policy.safety_reserve,
                }
            return row

        self._client.table("provider_budgets").upsert(
            {
                "provider": provider,
                "period_type": policy.period,
                "max_requests": policy.max_requests,
                "used_requests": 0,
                "safety_reserve": policy.safety_reserve,
                "reset_at": _next_reset(now, policy.period).isoformat(),
                "updated_at": now.isoformat(),
            },
            on_conflict="provider,period_type",
        ).execute()
        rows = self._select_rows(provider, policy.period)
        return rows[0] if rows else None

    def try_consume(self, provider: str, *, cost: int = 1) -> bool:
        if cost < 1:
            raise ValueError("Provider request cost must be >= 1")
        policy = self._policy(provider)
        now = self._clock()
        row = self._get_or_create_row(provider, policy, now)
        if row is None:
            return False

        reset_at = _parse_datetime(row.get("reset_at"))
        used = int(row.get("used_requests", 0))
        if reset_at is None or reset_at <= now:
            used = 0
            reset_at = _next_reset(now, policy.period)
            self._client.table("provider_budgets").update(
                {
                    "used_requests": 0,
                    "reset_at": reset_at.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ).eq("provider", provider).eq("period_type", policy.period).execute()

        limit = policy.max_requests - policy.safety_reserve
        if used + cost > limit:
            return False
        self._client.table("provider_budgets").update(
            {
                "used_requests": used + cost,
                "updated_at": now.isoformat(),
            }
        ).eq("provider", provider).eq("period_type", policy.period).execute()
        return True

    def requests_used(self, provider: str) -> int:
        policy = self._policy(provider)
        rows = self._select_rows(provider, policy.period, "used_requests,reset_at")
        if not rows:
            return 0
        reset_at = _parse_datetime(rows[0].get("reset_at"))
        if reset_at is None or reset_at <= self._clock():
            return 0
        return int(rows[0].get("used_requests", 0))


__all__ = [
    "InMemoryProviderBudgetRepository",
    "ProviderBudget",
    "ProviderBudgetRepository",
    "SupabaseProviderBudgetRepository",
]
