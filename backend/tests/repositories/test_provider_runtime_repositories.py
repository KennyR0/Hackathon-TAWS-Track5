from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.repositories.provider_budget_repository import InMemoryProviderBudgetRepository
from app.repositories.provider_cache_repository import (
    InMemoryProviderCacheRepository,
    ProviderCacheEntry,
    params_hash,
)
from app.repositories.provider_health_repository import InMemoryProviderHealthRepository
from app.services.provider_runtime_service import ProviderRuntimeBundle, store_probe_cache


def test_cache_hit_does_not_increment_budget() -> None:
    cache = InMemoryProviderCacheRepository()
    budget = InMemoryProviderBudgetRepository(max_requests=5)
    runtime = ProviderRuntimeBundle(cache=cache, budget=budget, health=InMemoryProviderHealthRepository())
    now = datetime.now(UTC)
    cache.put(
        ProviderCacheEntry(
            cache_key="probe:gdelt",
            provider="gdelt",
            request_params_hash=params_hash({"provider": "gdelt"}),
            response_json={"articleCount": 1},
            fetched_at=now,
            expires_at=now + timedelta(minutes=5),
            request_cost=1,
            status_code=200,
            data_mode="live",
        )
    )
    assert cache.get_valid("gdelt", "probe:gdelt") is not None
    assert budget.try_consume("gdelt") is True
    assert budget.requests_used("gdelt") == 1
    assert cache.get_valid("gdelt", "probe:gdelt") is not None


def test_expired_cache_not_returned() -> None:
    cache = InMemoryProviderCacheRepository()
    now = datetime.now(UTC)
    cache.put(
        ProviderCacheEntry(
            cache_key="probe:gdelt",
            provider="gdelt",
            request_params_hash=params_hash({"provider": "gdelt"}),
            response_json={"articleCount": 1},
            fetched_at=now - timedelta(hours=1),
            expires_at=now - timedelta(minutes=1),
            request_cost=1,
            status_code=200,
            data_mode="live",
        )
    )
    assert cache.get_valid("gdelt", "probe:gdelt") is None


def test_budget_never_negative() -> None:
    budget = InMemoryProviderBudgetRepository(max_requests=2, safety_reserve=0)
    assert budget.try_consume("gdelt") is True
    assert budget.try_consume("gdelt") is True
    assert budget.try_consume("gdelt") is False
    assert budget.requests_used("gdelt") == 2


def test_circuit_opens_after_failures() -> None:
    health = InMemoryProviderHealthRepository(failure_threshold=2)
    health.record_failure("gdelt")
    assert health.is_circuit_open("gdelt") is False
    health.record_failure("gdelt")
    assert health.is_circuit_open("gdelt") is True
    health.record_success("gdelt")
    assert health.is_circuit_open("gdelt") is False


def test_store_probe_cache_persists() -> None:
    cache = InMemoryProviderCacheRepository()
    budget = InMemoryProviderBudgetRepository(max_requests=5)
    runtime = ProviderRuntimeBundle(cache=cache, budget=budget, health=InMemoryProviderHealthRepository())
    store_probe_cache(
        runtime,
        provider="gdelt",
        cache_key="probe:gdelt",
        params={"provider": "gdelt"},
        response_json={"articleCount": 3},
        status_code=200,
        data_mode="live",
    )
    entry = cache.get_valid("gdelt", "probe:gdelt")
    assert entry is not None
    assert entry.response_json["articleCount"] == 3
