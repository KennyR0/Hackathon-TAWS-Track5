"""Analysis run services."""

from __future__ import annotations

from threading import Lock, Thread
from time import sleep

from app.config import DEFAULT_LLM_PROVIDER, get_openai_config, get_runtime_config
from app.contracts.api import AgentRunStepsResponse, AnalysisRequest, AnalysisResponse, SseEvent
from app.contracts.entities import AnalysisStatus, allow_internal_field_names
from app.llm.base import LLMAdapter
from app.repositories.fixture_repository import PROMPT_VERSION, FixtureRepository
from app.workflows.market_analysis_graph import run_market_analysis_workflow


class AnalysisService:
    def __init__(self, repository: FixtureRepository, llm_adapter: LLMAdapter) -> None:
        self._repository = repository
        self._llm_adapter = llm_adapter
        self._threads: dict[str, Thread] = {}
        self._thread_lock = Lock()

    def create_analysis(
        self,
        request: AnalysisRequest,
        *,
        idempotency_key: str,
    ) -> AnalysisResponse:
        runtime_config = get_runtime_config()
        model_name = (
            "fixture-llm"
            if runtime_config.llm_provider == DEFAULT_LLM_PROVIDER
            else get_openai_config().model
        )
        run, should_schedule = self._repository.create_analysis_run(
            request,
            idempotency_key=idempotency_key,
            model_name=model_name,
            prompt_version=PROMPT_VERSION,
        )
        if should_schedule:
            self._schedule_run(run.id, request)
        with allow_internal_field_names():
            return AnalysisResponse(
                data=self._repository.get_analysis_run(run.id),
                meta=self._repository.get_meta(),
            )

    def get_analysis(self, run_id: str) -> AnalysisResponse:
        with allow_internal_field_names():
            return AnalysisResponse(
                data=self._repository.get_analysis_run(run_id),
                meta=self._repository.get_meta(),
            )

    def list_run_steps(self, run_id: str) -> AgentRunStepsResponse:
        with allow_internal_field_names():
            return AgentRunStepsResponse(
                data=self._repository.get_run_steps(run_id),
                meta=self._repository.get_meta(),
            )

    def resolve_sse_cursor(self, run_id: str, last_event_id: str | None) -> int:
        steps = self._repository.get_run_steps(run_id)
        if last_event_id is None:
            return 0
        for index, step in enumerate(steps):
            if step.id == last_event_id:
                return index + 1
        return 0

    def poll_sse_events(
        self,
        run_id: str,
        start_index: int,
    ) -> tuple[tuple[SseEvent, ...], int, bool]:
        steps = self._repository.get_run_steps(run_id)
        run = self._repository.get_analysis_run(run_id)
        events = []
        for index, step in enumerate(steps[start_index:], start=start_index):
            is_last_emitted = index == len(steps) - 1 and run.status != AnalysisStatus.PROCESSING
            event_status = run.status if is_last_emitted else AnalysisStatus.PROCESSING
            with allow_internal_field_names():
                events.append(
                    SseEvent(
                        id=step.id,
                        run_id=step.run_id,
                        node=step.node,
                        status=event_status,
                        timestamp=step.timestamp,
                        payload=step.payload,
                    )
                )
        return tuple(events), len(steps), self._repository.is_run_terminal(run_id)

    def _schedule_run(self, run_id: str, request: AnalysisRequest) -> None:
        with self._thread_lock:
            thread = self._threads.get(run_id)
            if thread is not None and thread.is_alive():
                return
            thread = Thread(
                target=self._execute_run,
                args=(run_id, request),
                daemon=True,
                name=f"analysis-{run_id}",
            )
            self._threads[run_id] = thread
            thread.start()

    def _execute_run(self, run_id: str, request: AnalysisRequest) -> None:
        try:
            matched_signals = run_market_analysis_workflow(
                repository=self._repository,
                llm_adapter=self._llm_adapter,
                run_id=run_id,
                event_id=request.event_id,
                asset_ids=request.asset_ids,
                started_at=self._repository.get_analysis_run(run_id).started_at,
                step_sink=lambda step: self._repository.append_run_step(run_id, step),
            )
            terminal_status = (
                AnalysisStatus.COMPLETED
                if any(signal.analysis_status == AnalysisStatus.COMPLETED for signal in matched_signals)
                else AnalysisStatus.INSUFFICIENT_EVIDENCE
            )
            self._repository.complete_analysis_run(
                run_id,
                status=terminal_status.value,
                current_node="pending_review",
            )
        except Exception:
            self._repository.fail_analysis_run(
                run_id,
                current_node="failed",
                error_code="workflow_execution_failed",
            )

    def wait_until_terminal(self, run_id: str, *, max_polls: int = 200) -> None:
        for _ in range(max_polls):
            if self._repository.is_run_terminal(run_id):
                return
            sleep(0.01)
