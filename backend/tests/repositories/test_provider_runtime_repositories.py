from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import ProviderBudgetPolicy
from app.repositories.provider_budget_repository import (
    InMemoryProviderBudgetRepository,
    SupabaseProviderBudgetRepository,
)
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


def test_budget_uses_independent_provider_policies_and_resets_period() -> None:
    now = [datetime(2026, 7, 12, 10, 0, tzinfo=UTC)]
    budget = InMemoryProviderBudgetRepository(
        max_requests=10,
        provider_policies={
            "twelve_data": ProviderBudgetPolicy(
                period="minute",
                max_requests=3,
                safety_reserve=1,
            )
        },
        clock=lambda: now[0],
    )

    assert budget.try_consume("twelve_data") is True
    assert budget.try_consume("twelve_data") is True
    assert budget.try_consume("twelve_data") is False
    assert budget.try_consume("finnhub") is True
    assert budget.requests_used("twelve_data") == 2
    assert budget.requests_used("finnhub") == 1

    now[0] += timedelta(minutes=1)

    assert budget.requests_used("twelve_data") == 0
    assert budget.try_consume("twelve_data") is True


class _FakeResponse:
    def __init__(self, data) -> None:
        self.data = data


class _FakeBudgetQuery:
    def __init__(self, client, operation: str = "select", payload=None) -> None:
        self._client = client
        self._operation = operation
        self._payload = payload
        self._filters: dict[str, object] = {}

    def select(self, _columns: str):
        self._operation = "select"
        return self

    def eq(self, column: str, value: object):
        self._filters[column] = value
        return self

    def limit(self, _value: int):
        return self

    def upsert(self, payload, **_kwargs):
        self._operation = "upsert"
        self._payload = payload
        return self

    def update(self, payload):
        self._operation = "update"
        self._payload = payload
        return self

    def execute(self):
        if self._operation == "select":
            rows = [
                dict(row)
                for row in self._client.rows.values()
                if all(row.get(key) == value for key, value in self._filters.items())
            ]
            return _FakeResponse(rows)
        if self._operation == "upsert":
            self._client.upserts += 1
            key = (self._payload["provider"], self._payload["period_type"])
            self._client.rows[key] = dict(self._payload)
            return _FakeResponse([dict(self._payload)])
        for key, row in self._client.rows.items():
            if all(row.get(column) == value for column, value in self._filters.items()):
                self._client.rows[key] = {**row, **self._payload}
        return _FakeResponse([])


class _FakeBudgetClient:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, object]] = {}
        self.upserts = 0

    def table(self, name: str):
        assert name == "provider_budgets"
        return _FakeBudgetQuery(self)


def test_supabase_budget_does_not_reset_usage_on_every_consume() -> None:
    client = _FakeBudgetClient()
    budget = SupabaseProviderBudgetRepository(
        client,
        max_requests=3,
        clock=lambda: datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
    )

    assert budget.try_consume("twelve_data") is True
    assert budget.try_consume("twelve_data") is True

    row = client.rows[("twelve_data", "hour")]
    assert row["used_requests"] == 2
    assert client.upserts == 1


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
    runtime = ProviderRuntimeBundle(
        cache=cache,
        budget=budget,
        health=InMemoryProviderHealthRepository(),
    )
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
