"""Signal query services."""

from __future__ import annotations

from app.contracts.api import EvidenceListResponse, SignalListResponse, SignalResponse
from app.contracts.entities import AnalysisStatus, allow_internal_field_names
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
        signals = []
        for signal in self._repository.list_signals(
            instrument_type=instrument_type,
            asset=asset,
            published_after=published_after,
        ):
            enriched_signal = self._enrich_signal(signal)
            signals.append(enriched_signal)
        with allow_internal_field_names():
            return SignalListResponse(data=tuple(signals), meta=self._repository.get_meta())

    def get_signal(self, signal_id: str) -> SignalResponse:
        signal = self._enrich_signal(self._repository.get_signal(signal_id))
        with allow_internal_field_names():
            return SignalResponse(data=signal, meta=self._repository.get_meta())

    def get_signal_evidence(self, signal_id: str) -> EvidenceListResponse:
        with allow_internal_field_names():
            return EvidenceListResponse(
                data=self._repository.get_signal_evidence(signal_id),
                meta=self._repository.get_meta(),
            )

    def _enrich_signal(self, signal):
        if signal.price_reaction is not None or signal.analysis_status != AnalysisStatus.COMPLETED:
            return signal
        price_reaction = self._repository.calculate_signal_price_reaction(signal)
        if price_reaction is None:
            return signal
        return signal.model_copy(update={"price_reaction": price_reaction})

