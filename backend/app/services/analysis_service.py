"""Analysis run services."""

from __future__ import annotations

from app.config import DEFAULT_LLM_PROVIDER, get_runtime_config
from app.contracts.api import AgentRunStepsResponse, AnalysisRequest, AnalysisResponse, SseEvent
from app.contracts.entities import AnalysisStatus, allow_internal_field_names
from app.llm.base import LLMAdapter
from app.repositories.fixture_repository import PROMPT_VERSION, FixtureRepository
from app.workflows.market_analysis_graph import run_market_analysis_workflow


class AnalysisService:
    def __init__(self, repository: FixtureRepository, llm_adapter: LLMAdapter) -> None:
        self._repository = repository
        self._llm_adapter = llm_adapter

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
            else "gpt-5.4"
        )
        run = self._repository.create_analysis_run(
            request,
            idempotency_key=idempotency_key,
            model_name=model_name,
            prompt_version=PROMPT_VERSION,
        )
        run_market_analysis_workflow(
            repository=self._repository,
            llm_adapter=self._llm_adapter,
            run_id=run.id,
            event_id=request.event_id,
            asset_ids=request.asset_ids,
        )
        with allow_internal_field_names():
            return AnalysisResponse(data=self._repository.get_analysis_run(run.id), meta=self._repository.get_meta())

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

    def build_sse_events(self, run_id: str, last_event_id: str | None) -> tuple[SseEvent, ...]:
        steps = self._repository.get_run_steps(run_id)
        result = []
        replay_enabled = last_event_id is None
        for step in steps:
            if not replay_enabled and step.id == last_event_id:
                replay_enabled = True
                continue
            if not replay_enabled:
                continue
            with allow_internal_field_names():
                result.append(
                    SseEvent(
                        id=step.id,
                        run_id=step.run_id,
                        node=step.node,
                        status=AnalysisStatus.COMPLETED,
                        timestamp=step.timestamp,
                        payload=step.payload,
                    )
                )
        return tuple(result)
