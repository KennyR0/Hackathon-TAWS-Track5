"""Review mutation services."""

from __future__ import annotations

from app.contracts.api import ReviewListResponse, ReviewRequest
from app.contracts.entities import allow_internal_field_names
from app.repositories.fixture_repository import FixtureRepository


class ReviewService:
    def __init__(self, repository: FixtureRepository) -> None:
        self._repository = repository

    def list_reviews(self, signal_id: str) -> ReviewListResponse:
        with allow_internal_field_names():
            return ReviewListResponse(
                data=self._repository.list_signal_reviews(signal_id),
                meta=self._repository.get_meta(),
            )

    def create_review(
        self,
        signal_id: str,
        request: ReviewRequest,
        *,
        idempotency_key: str,
    ) -> ReviewListResponse:
        with allow_internal_field_names():
            return ReviewListResponse(
                data=self._repository.create_signal_review(
                    signal_id,
                    request,
                    idempotency_key=idempotency_key,
                ),
                meta=self._repository.get_meta(),
            )

