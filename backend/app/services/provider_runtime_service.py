"""Orchestrates durable provider cache, budget and circuit breaker state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.repositories.provider_budget_repository import (
    InMemoryProviderBudgetRepository,
    ProviderBudgetRepository,
    SupabaseProviderBudgetRepository,
)
from app.repositories.provider_cache_repository import (
    InMemoryProviderCacheRepository,
    ProviderCacheEntry,
    ProviderCacheRepository,
    SupabaseProviderCacheRepository,
    params_hash,
)
from app.repositories.provider_health_repository import (
    InMemoryProviderHealthRepository,
    ProviderHealthRepository,
    SupabaseProviderHealthRepository,
)
from supabase import Client


@dataclass(frozen=True)
class ProviderRuntimeBundle:
    cache: ProviderCacheRepository
    budget: ProviderBudgetRepository
    health: ProviderHealthRepository


def build_in_memory_provider_runtime(
    *,
    request_budget: int,
    safety_reserve: int = 0,
    failure_threshold: int = 1,
) -> ProviderRuntimeBundle:
    return ProviderRuntimeBundle(
        cache=InMemoryProviderCacheRepository(),
        budget=InMemoryProviderBudgetRepository(
            max_requests=request_budget,
            safety_reserve=safety_reserve,
        ),
        health=InMemoryProviderHealthRepository(failure_threshold=failure_threshold),
    )


def build_supabase_provider_runtime(
    client: Client,
    *,
    request_budget: int,
    safety_reserve: int = 0,
    failure_threshold: int = 1,
) -> ProviderRuntimeBundle:
    return ProviderRuntimeBundle(
        cache=SupabaseProviderCacheRepository(client),
        budget=SupabaseProviderBudgetRepository(
            client,
            max_requests=request_budget,
            safety_reserve=safety_reserve,
        ),
        health=SupabaseProviderHealthRepository(
            client,
            failure_threshold=failure_threshold,
        ),
    )


def cache_ttl_for_provider(provider: str) -> timedelta:
    if provider in {"gdelt", "finnhub"}:
        return timedelta(minutes=5)
    return timedelta(minutes=15)


def store_probe_cache(
    runtime: ProviderRuntimeBundle,
    *,
    provider: str,
    cache_key: str,
    params: dict[str, object],
    response_json: dict[str, object],
    status_code: int,
    data_mode: str,
) -> None:
    now = datetime.now(UTC)
    runtime.cache.put(
        ProviderCacheEntry(
            cache_key=cache_key,
            provider=provider,
            request_params_hash=params_hash(params),
            response_json=response_json,
            fetched_at=now,
            expires_at=now + cache_ttl_for_provider(provider),
            request_cost=1,
            status_code=status_code,
            data_mode=data_mode,
        )
    )


__all__ = [
    "ProviderRuntimeBundle",
    "build_in_memory_provider_runtime",
    "build_supabase_provider_runtime",
    "cache_ttl_for_provider",
    "store_probe_cache",
]
