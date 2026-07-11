"""Briefing endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_briefing_service
from app.contracts.api import BriefingRequest, BriefingResponse
from app.services.briefing_service import BriefingService

router = APIRouter(tags=["briefings"])


@router.post(
    "/briefings",
    response_model=BriefingResponse,
    operation_id="createBriefing",
    status_code=201,
)
def create_briefing(
    request: BriefingRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: BriefingService = Depends(get_briefing_service),
) -> BriefingResponse:
    return service.create_briefing(request, idempotency_key=idempotency_key)


@router.get(
    "/briefings/{briefing_id}",
    response_model=BriefingResponse,
    operation_id="getBriefing",
)
def get_briefing(
    briefing_id: str,
    service: BriefingService = Depends(get_briefing_service),
) -> BriefingResponse:
    return service.get_briefing(briefing_id)
