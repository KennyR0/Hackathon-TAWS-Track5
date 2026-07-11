"""Signal endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_signal_service
from app.contracts.api import EvidenceListResponse, SignalListResponse, SignalResponse
from app.services.signal_service import SignalService

router = APIRouter(tags=["signals"])


@router.get("/signals", response_model=SignalListResponse, operation_id="listSignals")
def list_signals(
    instrument_type: Annotated[str | None, Query(alias="instrumentType")] = None,
    asset: str | None = None,
    published_after: Annotated[str | None, Query(alias="publishedAfter")] = None,
    service: SignalService = Depends(get_signal_service),
) -> SignalListResponse:
    return service.list_signals(
        instrument_type=instrument_type,
        asset=asset,
        published_after=published_after,
    )


@router.get("/signals/{signal_id}", response_model=SignalResponse, operation_id="getSignal")
def get_signal(
    signal_id: str,
    service: SignalService = Depends(get_signal_service),
) -> SignalResponse:
    return service.get_signal(signal_id)


@router.get(
    "/signals/{signal_id}/evidence",
    response_model=EvidenceListResponse,
    operation_id="listSignalEvidence",
)
def get_signal_evidence(
    signal_id: str,
    service: SignalService = Depends(get_signal_service),
) -> EvidenceListResponse:
    return service.get_signal_evidence(signal_id)
