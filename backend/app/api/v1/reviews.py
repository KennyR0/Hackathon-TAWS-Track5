"""Review endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.api.dependencies import get_review_service
from app.contracts.api import ReviewListResponse, ReviewRequest
from app.services.review_service import ReviewService

router = APIRouter(tags=["reviews"])


@router.get(
    "/signals/{signal_id}/reviews",
    response_model=ReviewListResponse,
    operation_id="listSignalReviews",
)
def list_signal_reviews(
    signal_id: str,
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    return service.list_reviews(signal_id)


@router.post(
    "/signals/{signal_id}/reviews",
    response_model=ReviewListResponse,
    operation_id="createSignalReview",
    status_code=201,
)
def create_signal_review(
    signal_id: str,
    request: ReviewRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: ReviewService = Depends(get_review_service),
) -> ReviewListResponse:
    return service.create_review(
        signal_id,
        request,
        idempotency_key=idempotency_key,
    )
