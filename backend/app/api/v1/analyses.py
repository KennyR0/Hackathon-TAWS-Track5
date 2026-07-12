"""Analysis endpoints."""

from __future__ import annotations

import json
from time import sleep
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_analysis_service
from app.contracts.api import AgentRunStepsResponse, AnalysisRequest, AnalysisResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(tags=["analyses"])


@router.post(
    "/analyses",
    response_model=AnalysisResponse,
    operation_id="createAnalysis",
    status_code=202,
)
def create_analysis(
    request: AnalysisRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    return service.create_analysis(request, idempotency_key=idempotency_key)


@router.get(
    "/analyses/{run_id}",
    response_model=AnalysisResponse,
    operation_id="getAnalysis",
)
def get_analysis(
    run_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResponse:
    return service.get_analysis(run_id)


@router.get("/analyses/{run_id}/stream", operation_id="streamAnalysis")
def stream_analysis(
    run_id: str,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    last_event_id_query: Annotated[str | None, Query(alias="lastEventId")] = None,
    service: AnalysisService = Depends(get_analysis_service),
) -> StreamingResponse:
    start_index = service.resolve_sse_cursor(run_id, last_event_id or last_event_id_query)

    def iter_events():
        cursor = start_index
        yield ": heartbeat\n\n"
        while True:
            events, cursor, is_terminal = service.poll_sse_events(run_id, cursor)
            if not events and is_terminal:
                return
            if not events:
                yield ": heartbeat\n\n"
                sleep(0.01)
                continue
            for event in events:
                payload = event.model_dump(mode="json", by_alias=True)
                yield f"id: {event.id}\n"
                yield "event: analysis-step\n"
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if is_terminal:
                return

    return StreamingResponse(iter_events(), media_type="text/event-stream")


@router.get(
    "/runs/{run_id}/steps",
    response_model=AgentRunStepsResponse,
    operation_id="listAgentRunSteps",
)
def list_agent_run_steps(
    run_id: str,
    service: AnalysisService = Depends(get_analysis_service),
) -> AgentRunStepsResponse:
    return service.list_run_steps(run_id)
