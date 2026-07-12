"""Supabase-backed durable overlay for the fixture-first repository."""

from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

from supabase import Client

from app.contracts.api import AgentRunStep, AnalysisRequest, BriefingRequest, ReviewRequest
from app.contracts.entities import (
    AgentRun,
    Briefing,
    Event,
    Evidence,
    Reviewer,
    Signal,
    SignalReview,
    allow_internal_field_names,
)
from app.contracts.fixtures import canonical_json_bytes
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService
from app.repositories.fixture_repository import REVIEWER, FixtureRepository


class SupabaseRepository(FixtureRepository):
    """Keep deterministic reads while persisting mutable workflow state."""

    def __init__(
        self,
        provider: FixtureProvider,
        client: Client,
        market_runtime: MarketDataRuntimeService | None = None,
        *,
        organization_id: str = "org_demo",
        actor_user_id: str | None = None,
    ) -> None:
        self._supabase = client
        self._organization_id = organization_id
        self._actor_user_id = actor_user_id
        self._enforce_ownership = actor_user_id is not None
        super().__init__(provider, market_runtime=market_runtime)
        self._hydrate_mutable_state()

    def _hydrate_mutable_state(self) -> None:
        signal_ids = self._owned_ids("signals") if self._enforce_ownership else ()
        if self._enforce_ownership:
            review_rows = []
            if signal_ids:
                review_rows = (
                self._supabase.table("signal_reviews")
                .select("*")
                .in_("signal_id", signal_ids)
                .execute()
                .data
                or []
            )
        else:
            review_rows = self._supabase.table("signal_reviews").select("*").execute().data or []
        with allow_internal_field_names():
            reviewer = Reviewer(**REVIEWER)
        for row in review_rows:
            if any(
                item.id == row["id"]
                for item in self._reviews_by_signal.get(row["signal_id"], [])
            ):
                continue
            with allow_internal_field_names():
                review = SignalReview(
                    id=row["id"],
                    signal_id=row["signal_id"],
                    previous_status=row["previous_status"],
                    status=row["status"],
                    justification=row["justification"],
                    reviewed_by=reviewer,
                    reviewed_at=row["reviewed_at"],
                    created_at=row["created_at"],
                )
            self._reviews_by_signal[review.signal_id].append(review)
            signal = self._signal_seeds.get(review.signal_id)
            if signal is not None:
                self._signal_seeds[review.signal_id] = signal.model_copy(
                    update={
                        "review": self._review_summary(review),
                        "updated_at": review.created_at,
                    }
                )

        idempotency_query = self._supabase.table("idempotency_keys").select(
            "operation,idempotency_key,request_hash,response_body"
        )
        if self._enforce_ownership:
            idempotency_query = idempotency_query.eq("organization_id", self._organization_id)
        idempotency_rows = idempotency_query.execute().data or []
        for row in idempotency_rows:
            body = row.get("response_body") or {}
            operation = row["operation"]
            if operation == "briefing" and body:
                briefing = Briefing.model_validate(body)
                self._briefings[briefing.briefing_id] = briefing

        run_query = self._supabase.table("agent_runs").select("*")
        if self._enforce_ownership:
            run_query = run_query.eq("organization_id", self._organization_id)
        run_rows = run_query.execute().data or []
        link_rows = (
            self._supabase.table("agent_run_source_snapshots").select("*").execute().data or []
        )
        snapshots_by_run: dict[str, list[str]] = {}
        for row in link_rows:
            snapshots_by_run.setdefault(row["run_id"], []).append(row["snapshot_id"])
        for row in run_rows:
            with allow_internal_field_names():
                run = AgentRun(
                    id=row["id"],
                    organization_id=row["organization_id"],
                    conversation_id=row["conversation_id"],
                    current_node=row["current_node"],
                    status=row["status"],
                    model_name=row["model_name"],
                    prompt_version=row["prompt_version"],
                    input_hash=row["input_hash"],
                    source_snapshot_ids=tuple(sorted(snapshots_by_run.get(row["id"], []))),
                    started_at=row["started_at"],
                    finished_at=row["finished_at"],
                    error_code=row["error_code"],
                    retry_count=row["retry_count"],
                )
            self._runs[run.id] = run

        step_rows = self._supabase.table("agent_run_steps").select("*").execute().data or []
        for row in step_rows:
            with allow_internal_field_names():
                step = AgentRunStep(
                    id=row["id"],
                    run_id=row["run_id"],
                    node=row["node"],
                    status=row["status"],
                    timestamp=row["step_at"],
                    payload=row["payload"],
                )
            self._run_steps[step.run_id].append(step)
        for run_id, steps in self._run_steps.items():
            self._run_steps[run_id] = sorted(steps, key=lambda item: item.timestamp)

    def _owned_ids(self, table: str) -> tuple[str, ...]:
        rows = (
            self._supabase.table(table)
            .select("id")
            .eq("organization_id", self._organization_id)
            .execute()
            .data
            or []
        )
        return tuple(str(row["id"]) for row in rows)

    def _assert_owned(self, table: str, resource_id: str) -> None:
        if not self._enforce_ownership:
            return
        rows = (
            self._supabase.table(table)
            .select("id")
            .eq("id", resource_id)
            .eq("organization_id", self._organization_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise KeyError("Resource not found")

    def list_events(self, **filters: str | None) -> tuple[tuple[Event, tuple[str, ...]], ...]:
        owned = set(self._owned_ids("events"))
        return tuple(item for item in super().list_events(**filters) if item[0].id in owned)

    def get_event(self, event_id: str) -> tuple[Event, tuple[str, ...]]:
        self._assert_owned("events", event_id)
        return super().get_event(event_id)

    def list_signals(self, **filters: str | None) -> tuple[Signal, ...]:
        owned = set(self._owned_ids("signals"))
        return tuple(item for item in super().list_signals(**filters) if item.id in owned)

    def get_signal(self, signal_id: str) -> Signal:
        self._assert_owned("signals", signal_id)
        return super().get_signal(signal_id)

    def get_signal_evidence(self, signal_id: str) -> tuple[Evidence, ...]:
        self._assert_owned("signals", signal_id)
        return super().get_signal_evidence(signal_id)

    def list_signal_reviews(self, signal_id: str) -> tuple[SignalReview, ...]:
        self._assert_owned("signals", signal_id)
        return super().list_signal_reviews(signal_id)

    def get_briefing(self, briefing_id: str) -> Briefing:
        self._assert_owned("briefings", briefing_id)
        return super().get_briefing(briefing_id)

    def get_analysis_run(self, run_id: str) -> AgentRun:
        self._assert_owned("agent_runs", run_id)
        return super().get_analysis_run(run_id)

    @staticmethod
    def _review_summary(review: SignalReview):
        from app.contracts.entities import ReviewSummary

        with allow_internal_field_names():
            return ReviewSummary(
                status=review.status,
                justification=review.justification,
                reviewed_by=review.reviewed_by,
                reviewed_at=review.reviewed_at,
            )

    def _persist_idempotency(
        self,
        *,
        operation: str,
        key: str,
        payload: bytes,
        response_body: Any,
    ) -> None:
        self._supabase.table("idempotency_keys").upsert(
            {
                "organization_id": self._organization_id,
                "operation": operation,
                "idempotency_key": key,
                "request_hash": f"sha256:{sha256(payload).hexdigest()}",
                "response_status": 200,
                "response_body": response_body,
                "expires_at": (self.fixture_clock + timedelta(days=1)).isoformat(),
            },
            on_conflict="organization_id,operation,idempotency_key",
        ).execute()

    def _persist_audit_event(
        self,
        *,
        audit_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        metadata: dict[str, Any],
        created_at: datetime,
        actor_user_id: str | None = None,
    ) -> None:
        self._supabase.table("audit_events").upsert(
            {
                "id": audit_id,
                "organization_id": self._organization_id,
                "actor_user_id": actor_user_id or self._actor_user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "metadata": metadata,
                "created_at": created_at.isoformat(),
            }
        ).execute()

    def _get_idempotency(
        self,
        operation: str,
        key: str,
        payload: bytes,
    ) -> dict[str, Any] | list[Any] | None:
        rows = (
            self._supabase.table("idempotency_keys")
            .select("request_hash,response_body")
            .eq("organization_id", self._organization_id)
            .eq("operation", operation)
            .eq("idempotency_key", key)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        if rows[0]["request_hash"] != f"sha256:{sha256(payload).hexdigest()}":
            raise ValueError("Idempotency-Key already used with a different payload")
        return rows[0].get("response_body")

    def create_signal_review(
        self,
        signal_id: str,
        request: ReviewRequest,
        *,
        idempotency_key: str,
        reviewer: Reviewer | None = None,
    ) -> tuple[SignalReview, ...]:
        payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
        previous = self._get_idempotency(
            f"review:{signal_id}",
            idempotency_key,
            payload,
        )
        if previous is not None:
            return self.list_signal_reviews(signal_id)

        before = {item.id for item in self.list_signal_reviews(signal_id)}
        reviews = super().create_signal_review(
            signal_id,
            request,
            idempotency_key=idempotency_key,
            reviewer=reviewer,
        )
        created = next((item for item in reviews if item.id not in before), None)
        if created is not None:
            self._supabase.table("signal_reviews").insert(
                {
                    "id": created.id,
                    "signal_id": created.signal_id,
                    "previous_status": created.previous_status.value,
                    "status": created.status.value,
                    "justification": created.justification,
                    "reviewed_by": created.reviewed_by.id,
                    "reviewed_at": created.reviewed_at.isoformat(),
                    "created_at": created.created_at.isoformat(),
                }
            ).execute()
            self._persist_idempotency(
                operation=f"review:{signal_id}",
                key=idempotency_key,
                payload=payload,
                response_body=[
                    item.model_dump(mode="json", by_alias=True)
                    for item in reviews
                ],
            )
            self._persist_audit_event(
                audit_id=f"audit_review_{created.id}",
                entity_type="signal_review",
                entity_id=signal_id,
                action=f"review_{created.status.value}",
                metadata={
                    "reviewId": created.id,
                    "previousStatus": created.previous_status.value,
                    "status": created.status.value,
                    "justification": created.justification,
                },
                created_at=created.created_at,
                actor_user_id=created.reviewed_by.id,
            )
        return reviews

    def create_briefing(
        self,
        request: BriefingRequest,
        *,
        idempotency_key: str,
        executive_summary: str,
    ) -> Briefing:
        payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
        previous = self._get_idempotency("briefing", idempotency_key, payload)
        if isinstance(previous, dict):
            return Briefing.model_validate(previous)

        briefing = super().create_briefing(
            request,
            idempotency_key=idempotency_key,
            executive_summary=executive_summary,
        )
        summary = briefing.human_review_summary
        self._supabase.table("briefings").upsert(
            {
                "id": briefing.briefing_id,
                "organization_id": self._organization_id,
                "watchlist_id": briefing.watchlist.id,
                "status": briefing.status.value,
                "executive_summary": briefing.executive_summary,
                "total_signals": summary.total_signals,
                "pending_review_count": summary.pending_review,
                "reviewed_count": summary.reviewed,
                "escalated_count": summary.escalated,
                "discarded_count": summary.discarded,
                "requires_human_review": True,
                "disclaimer": briefing.disclaimer,
                "created_at": briefing.created_at.isoformat(),
                "updated_at": briefing.updated_at.isoformat(),
            }
        ).execute()

        rows = [
            {
                "briefing_id": briefing.briefing_id,
                "signal_id": item.signal_id,
                "priority": item.priority,
                "reason": item.reason,
                "suggested_research_actions": list(item.suggested_research_actions),
                "position": index,
            }
            for index, item in enumerate(briefing.prioritized_signals)
        ]
        if rows:
            self._supabase.table("briefing_signals").upsert(rows).execute()

        self._persist_idempotency(
            operation="briefing",
            key=idempotency_key,
            payload=payload,
            response_body=briefing.model_dump(mode="json", by_alias=True),
        )
        self._persist_audit_event(
            audit_id=f"audit_briefing_{briefing.briefing_id}",
            entity_type="briefing",
            entity_id=briefing.briefing_id,
            action=f"briefing_{briefing.status.value}",
            metadata={
                "signalIds": [item.signal_id for item in briefing.prioritized_signals],
                "reviewTaskCount": len(briefing.review_tasks),
                "status": briefing.status.value,
            },
            created_at=briefing.created_at,
        )
        return briefing

    def create_analysis_run(
        self,
        request: AnalysisRequest,
        *,
        idempotency_key: str,
        model_name: str,
        prompt_version: str,
    ) -> tuple[AgentRun, bool]:
        payload = canonical_json_bytes(request.model_dump(mode="json", by_alias=True))
        previous = self._get_idempotency("analysis", idempotency_key, payload)
        if isinstance(previous, dict):
            return self.get_analysis_run(previous["id"]), False

        run, is_created = super().create_analysis_run(
            request,
            idempotency_key=idempotency_key,
            model_name=model_name,
            prompt_version=prompt_version,
        )
        run = run.model_copy(update={"organization_id": self._organization_id})
        self._runs[run.id] = run
        if is_created:
            self._persist_run(run)
            links = [
                {
                    "run_id": run.id,
                    "snapshot_id": snapshot_id,
                    "snapshot_kind": (
                        "market" if snapshot_id.startswith("mkt_") else "raw_source"
                    ),
                }
                for snapshot_id in run.source_snapshot_ids
            ]
            if links:
                existing_links = (
                    self._supabase.table("agent_run_source_snapshots")
                    .select("run_id,snapshot_id")
                    .eq("run_id", run.id)
                    .execute()
                    .data
                    or []
                )
                existing_pairs = {
                    (row["run_id"], row["snapshot_id"])
                    for row in existing_links
                }
                rows_to_insert = [
                    row
                    for row in links
                    if (row["run_id"], row["snapshot_id"]) not in existing_pairs
                ]
                if rows_to_insert:
                    self._supabase.table("agent_run_source_snapshots").insert(rows_to_insert).execute()
            self._persist_idempotency(
                operation="analysis",
                key=idempotency_key,
                payload=payload,
                response_body=run.model_dump(mode="json", by_alias=True),
            )
            self._persist_audit_event(
                audit_id=f"audit_run_{run.id}_scheduled",
                entity_type="agent_run",
                entity_id=run.id,
                action="analysis_scheduled",
                metadata={
                    "eventId": request.event_id,
                    "assetIds": list(request.asset_ids),
                    "sourceSnapshotIds": list(run.source_snapshot_ids),
                },
                created_at=run.started_at,
            )
        return run, is_created

    def _persist_run(self, run: AgentRun) -> None:
        self._supabase.table("agent_runs").upsert(
            {
                "id": run.id,
                "organization_id": run.organization_id,
                "conversation_id": run.conversation_id,
                "current_node": run.current_node,
                "status": run.status.value,
                "model_name": run.model_name,
                "prompt_version": run.prompt_version,
                "input_hash": run.input_hash,
                "started_at": run.started_at.isoformat(),
                "finished_at": (
                    run.finished_at.isoformat()
                    if run.finished_at is not None
                    else None
                ),
                "error_code": run.error_code,
                "retry_count": run.retry_count,
            }
        ).execute()

    def append_run_step(self, run_id: str, step: AgentRunStep) -> None:
        existing_step_ids = {item.id for item in self.get_run_steps(run_id)}
        super().append_run_step(run_id, step)
        if step.id in existing_step_ids:
            return
        self._supabase.table("agent_run_steps").insert(
            {
                "id": step.id,
                "run_id": step.run_id,
                "node": step.node,
                "status": step.status,
                "step_at": step.timestamp.isoformat(),
                "payload": step.payload,
            }
        ).execute()
        self._persist_audit_event(
            audit_id=f"audit_step_{step.id}",
            entity_type="agent_run_step",
            entity_id=run_id,
            action=f"node_{step.node}",
            metadata={
                "node": step.node,
                "status": step.status,
                "payload": step.payload,
            },
            created_at=step.timestamp,
        )
        self._persist_run(self.get_analysis_run(run_id))

    def complete_analysis_run(
        self,
        run_id: str,
        *,
        status: str,
        current_node: str,
    ) -> AgentRun:
        run = super().complete_analysis_run(
            run_id,
            status=status,
            current_node=current_node,
        )
        self._persist_run(run)
        if run.finished_at is not None:
            self._persist_audit_event(
                audit_id=f"audit_run_{run.id}_completed",
                entity_type="agent_run",
                entity_id=run.id,
                action=f"analysis_{run.status.value}",
                metadata={
                    "currentNode": run.current_node,
                    "status": run.status.value,
                    "errorCode": run.error_code,
                },
                created_at=run.finished_at,
            )
        return run

    def fail_analysis_run(
        self,
        run_id: str,
        *,
        current_node: str,
        error_code: str,
    ) -> AgentRun:
        run = super().fail_analysis_run(
            run_id,
            current_node=current_node,
            error_code=error_code,
        )
        self._persist_run(run)
        if run.finished_at is not None:
            self._persist_audit_event(
                audit_id=f"audit_run_{run.id}_failed",
                entity_type="agent_run",
                entity_id=run.id,
                action="analysis_failed",
                metadata={
                    "currentNode": run.current_node,
                    "status": run.status.value,
                    "errorCode": run.error_code,
                },
                created_at=run.finished_at,
            )
        return run


__all__ = ["SupabaseRepository"]
