"""Signal query services."""

from __future__ import annotations

from app.contracts.api import EvidenceListResponse, SignalListResponse, SignalResponse
from app.contracts.entities import allow_internal_field_names
from app.repositories.fixture_repository import FixtureRepository


class SignalService:
    def __init__(self, repository: FixtureRepository) -> None:
        self._repository = repository

    def list_signals(
        self,
        *,
        instrument_type: str | None = None,
        asset: str | None = None,
        published_after: str | None = None,
    ) -> SignalListResponse:
        with allow_internal_field_names():
            return SignalListResponse(
                data=self._repository.list_signals(
                    instrument_type=instrument_type,
                    asset=asset,
                    published_after=published_after,
                ),
                meta=self._repository.get_meta(),
            )

    def get_signal(self, signal_id: str) -> SignalResponse:
        with allow_internal_field_names():
            return SignalResponse(data=self._repository.get_signal(signal_id), meta=self._repository.get_meta())

    def get_signal_evidence(self, signal_id: str) -> EvidenceListResponse:
        with allow_internal_field_names():
            return EvidenceListResponse(
                data=self._repository.get_signal_evidence(signal_id),
                meta=self._repository.get_meta(),
            )
