"""Phase 10 differentiator endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_differentiator_service
from app.contracts.api import EcuadorSnapshotListResponse, SimilarEventListResponse
from app.services.differentiator_service import DifferentiatorService

router = APIRouter(tags=["differentiators"])
DifferentiatorServiceDep = Annotated[DifferentiatorService, Depends(get_differentiator_service)]


@router.get(
    "/events/{event_id}/similar",
    response_model=SimilarEventListResponse,
    operation_id="listSimilarEvents",
)
def list_similar_events(
    event_id: str,
    service: DifferentiatorServiceDep,
) -> SimilarEventListResponse:
    return service.list_similar_events(event_id)


@router.get(
    "/ecuador-snapshots",
    response_model=EcuadorSnapshotListResponse,
    operation_id="listEcuadorSnapshots",
)
def list_ecuador_snapshots(
    service: DifferentiatorServiceDep,
) -> EcuadorSnapshotListResponse:
    return service.list_ecuador_snapshots()
