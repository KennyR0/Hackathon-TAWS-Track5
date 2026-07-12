"""Briefing services."""

from __future__ import annotations

from app.contracts.api import BriefingRequest, BriefingResponse
from app.contracts.entities import allow_internal_field_names
from app.llm.base import LLMAdapter
from app.repositories.fixture_repository import FixtureRepository


class BriefingService:
    def __init__(self, repository: FixtureRepository, llm_adapter: LLMAdapter) -> None:
        self._repository = repository
        self._llm_adapter = llm_adapter

    def create_briefing(
        self,
        request: BriefingRequest,
        *,
        idempotency_key: str,
    ) -> BriefingResponse:
        signals = tuple(self._repository.get_signal(signal_id) for signal_id in request.signal_ids)
        briefing_output = self._llm_adapter.build_briefing(signals)
        briefing = self._repository.create_briefing(
            request,
            idempotency_key=idempotency_key,
            executive_summary=briefing_output.executive_summary,
        )
        with allow_internal_field_names():
            return BriefingResponse(data=briefing, meta=self._repository.get_meta())

    def get_briefing(self, briefing_id: str) -> BriefingResponse:
        with allow_internal_field_names():
            return BriefingResponse(
                data=self._repository.get_briefing(briefing_id),
                meta=self._repository.get_meta(),
            )
