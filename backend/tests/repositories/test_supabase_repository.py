from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.contracts.api import AgentRunStep, AnalysisRequest, BriefingRequest, ReviewRequest
from app.providers.fixture_provider import FixtureProvider
from app.repositories.supabase_repository import SupabaseRepository


def _identity_for_table(table: str, row: dict[str, Any]) -> tuple[Any, ...]:
    if table == "idempotency_keys":
        return (
            row["organization_id"],
            row["operation"],
            row["idempotency_key"],
        )
    if table == "briefing_signals":
        return (row["briefing_id"], row["signal_id"])
    if table == "agent_run_source_snapshots":
        return (row["run_id"], row["snapshot_id"])
    return (row["id"],)


class FakeQuery:
    def __init__(self, client: FakeClient, table: str) -> None:
        self.client = client
        self.table = table
        self.filters: list[tuple[str, Any]] = []
        self.payload: dict[str, Any] | list[dict[str, Any]] | None = None
        self.operation = "select"
        self.limit_count: int | None = None

    def select(self, _columns: str) -> FakeQuery:
        return self

    def eq(self, column: str, value: Any) -> FakeQuery:
        self.filters.append((column, value))
        return self

    def in_(self, column: str, values: tuple[str, ...]) -> FakeQuery:
        self.filters.append((column, set(values)))
        return self

    def limit(self, count: int) -> FakeQuery:
        self.limit_count = count
        return self

    def insert(self, payload: dict[str, Any]) -> FakeQuery:
        self.operation = "insert"
        self.payload = payload
        return self

    def upsert(self, payload, **_kwargs) -> FakeQuery:
        self.operation = "upsert"
        self.payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> FakeQuery:
        self.operation = "update"
        self.payload = payload
        return self

    def execute(self):
        rows = self.client.rows.setdefault(self.table, [])
        if self.operation == "select":
            selected = [
                row
                for row in rows
                if all(
                    row.get(column) in value if isinstance(value, set) else row.get(column) == value
                    for column, value in self.filters
                )
            ]
            if self.limit_count is not None:
                selected = selected[: self.limit_count]
            return SimpleNamespace(data=selected)

        payloads = self.payload if isinstance(self.payload, list) else [self.payload]
        assert payloads is not None

        if self.operation == "insert":
            for payload in payloads:
                assert payload is not None
                rows.append(dict(payload))
            return SimpleNamespace(data=payloads)

        if self.operation == "upsert":
            for payload in payloads:
                assert payload is not None
                identity = _identity_for_table(self.table, payload)
                existing_index = next(
                    (
                        index
                        for index, row in enumerate(rows)
                        if _identity_for_table(self.table, row) == identity
                    ),
                    None,
                )
                if existing_index is None:
                    rows.append(dict(payload))
                else:
                    rows[existing_index] = {**rows[existing_index], **dict(payload)}
            return SimpleNamespace(data=payloads)

        if self.operation == "update":
            updated = []
            for row in rows:
                if all(row.get(column) == value for column, value in self.filters):
                    row.update(dict(payloads[0]))
                    updated.append(dict(row))
            return SimpleNamespace(data=updated)

        raise AssertionError(f"Unsupported operation: {self.operation}")


class FakeClient:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)


def _repository(client: FakeClient) -> SupabaseRepository:
    bundle = Path(__file__).resolve().parents[3] / "data/fixtures/v1/phase0_bundle.json"
    return SupabaseRepository(FixtureProvider(bundle), client)


def test_authenticated_repository_hides_other_organization_resources() -> None:
    client = FakeClient()
    client.rows["signals"] = [
        {"id": "sig_wti_context", "organization_id": "org_other"},
    ]
    bundle = Path(__file__).resolve().parents[3] / "data/fixtures/v1/phase0_bundle.json"
    repository = SupabaseRepository(
        FixtureProvider(bundle),
        client,
        organization_id="org_demo",
        actor_user_id="usr_demo",
    )

    try:
        repository.get_signal("sig_wti_context")
    except KeyError as exc:
        assert str(exc.args[0]) == "Resource not found"
    else:
        raise AssertionError("Cross-organization signal must not be visible")


def test_review_persists_and_rehydrates_after_repository_restart() -> None:
    client = FakeClient()
    first = _repository(client)
    request = ReviewRequest.model_validate(
        {"status": "reviewed", "justification": "Persistencia verificada."}
    )

    created = first.create_signal_review(
        "sig_wti_context",
        request,
        idempotency_key="supabase-review-test-001",
    )
    restarted = _repository(client)

    assert created[-1].status.value == "reviewed"
    assert restarted.get_signal("sig_wti_context").review.status.value == "reviewed"
    assert restarted.list_signal_reviews("sig_wti_context")[-1].justification == (
        "Persistencia verificada."
    )
    assert client.rows["audit_events"][-1]["action"] == "review_reviewed"
    assert client.rows["audit_events"][-1]["actor_user_id"] == "usr_analista_demo"


def test_review_idempotency_rejects_different_payload_after_restart() -> None:
    client = FakeClient()
    first = _repository(client)
    first.create_signal_review(
        "sig_wti_context",
        ReviewRequest.model_validate(
            {"status": "reviewed", "justification": "Primera revision."}
        ),
        idempotency_key="supabase-review-test-002",
    )
    restarted = _repository(client)

    try:
        restarted.create_signal_review(
            "sig_wti_context",
            ReviewRequest.model_validate(
                {"status": "discarded", "justification": "Payload distinto."}
            ),
            idempotency_key="supabase-review-test-002",
        )
    except ValueError as error:
        assert "different payload" in str(error)
    else:
        raise AssertionError("different payload must be rejected")


def test_briefing_idempotency_replays_same_briefing_after_restart() -> None:
    client = FakeClient()
    first = _repository(client)
    request = BriefingRequest.model_validate(
        {
            "watchlistId": "watchlist_demo_global",
            "signalIds": ["sig_aapl_negative", "sig_wti_context"],
            "status": "draft",
        }
    )

    first_briefing = first.create_briefing(
        request,
        idempotency_key="supabase-briefing-test-001",
        executive_summary="Resumen de prueba persistente.",
    )
    restarted = _repository(client)
    replayed = restarted.create_briefing(
        request,
        idempotency_key="supabase-briefing-test-001",
        executive_summary="No debe cambiar.",
    )

    assert replayed.briefing_id == first_briefing.briefing_id
    assert len(client.rows["briefings"]) == 1
    assert len(client.rows["briefing_signals"]) == 2


def test_analysis_run_and_steps_persist_after_restart() -> None:
    client = FakeClient()
    first = _repository(client)
    request = AnalysisRequest.model_validate(
        {
            "eventId": "evt_aapl_outlook_20260709",
            "assetIds": ["ast_aapl"],
        }
    )

    run, is_created = first.create_analysis_run(
        request,
        idempotency_key="supabase-analysis-test-001",
        model_name="fixture-llm",
        prompt_version="test-v1",
    )
    step = AgentRunStep.model_validate(
        {
            "id": "step_supabase_001",
            "runId": run.id,
            "node": "load_context",
            "status": "processing",
            "timestamp": datetime(2026, 7, 12, 12, 0, tzinfo=timezone.utc),
            "payload": {"eventId": request.event_id},
        }
    )
    first.append_run_step(run.id, step)
    first.complete_analysis_run(
        run.id,
        status="completed",
        current_node="pending_review",
    )
    restarted = _repository(client)
    replayed, replay_is_created = restarted.create_analysis_run(
        request,
        idempotency_key="supabase-analysis-test-001",
        model_name="fixture-llm",
        prompt_version="test-v1",
    )

    assert is_created is True
    assert replay_is_created is False
    assert replayed.id == run.id
    assert restarted.get_analysis_run(run.id).status.value == "completed"
    assert restarted.get_run_steps(run.id)[0].id == "step_supabase_001"
    assert any(
        row["action"] == "analysis_scheduled"
        for row in client.rows["audit_events"]
    )
    assert any(
        row["action"] == "node_load_context"
        for row in client.rows["audit_events"]
    )
    assert any(
        row["action"] == "analysis_completed"
        for row in client.rows["audit_events"]
    )


def test_duplicate_run_step_is_not_reinserted_after_restart() -> None:
    client = FakeClient()
    first = _repository(client)
    request = AnalysisRequest.model_validate(
        {
            "eventId": "evt_aapl_outlook_20260709",
            "assetIds": ["ast_aapl"],
        }
    )
    run, _ = first.create_analysis_run(
        request,
        idempotency_key="supabase-analysis-test-002",
        model_name="fixture-llm",
        prompt_version="test-v1",
    )
    step = AgentRunStep.model_validate(
        {
            "id": "step_supabase_002",
            "runId": run.id,
            "node": "verify_sources",
            "status": "completed",
            "timestamp": datetime(2026, 7, 12, 12, 1, tzinfo=timezone.utc),
            "payload": {"warnings": []},
        }
    )
    first.append_run_step(run.id, step)

    restarted = _repository(client)
    restarted.append_run_step(run.id, step)

    rows = [
        row for row in client.rows["agent_run_steps"]
        if row["id"] == "step_supabase_002"
    ]
    assert len(rows) == 1
