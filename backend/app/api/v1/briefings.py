"""Briefing endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_briefing_service, get_current_app_user
from app.contracts.api import BriefingRequest, BriefingResponse
from app.contracts.entities import BriefingStatus
from app.security.auth import AppUserContext
from app.security.permissions import assert_can_create_shareable_briefing
from app.services.briefing_service import BriefingService

router = APIRouter(tags=["briefings"])
BriefingServiceDep = Annotated[BriefingService, Depends(get_briefing_service)]
CurrentUser = Annotated[AppUserContext, Depends(get_current_app_user)]


@router.post(
    "/briefings",
    response_model=BriefingResponse,
    operation_id="createBriefing",
    status_code=201,
)
def create_briefing(
    request: BriefingRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    user: CurrentUser,
    service: BriefingServiceDep,
) -> BriefingResponse:
    if request.status == BriefingStatus.SHAREABLE:
        assert_can_create_shareable_briefing(user)
    return service.create_briefing(request, idempotency_key=idempotency_key)


@router.get(
    "/briefings/{briefing_id}",
    response_model=BriefingResponse,
    operation_id="getBriefing",
)
def get_briefing(
    briefing_id: str,
    user: CurrentUser,
    service: BriefingServiceDep,
) -> BriefingResponse:
    _ = user
    return service.get_briefing(briefing_id)
