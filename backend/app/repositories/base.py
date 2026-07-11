"""Repository interfaces for backend data access."""

from __future__ import annotations

from typing import Protocol

from app.contracts.api import AgentRunStep, AnalysisRequest, BriefingRequest, ReviewRequest, Watchlist
from app.contracts.entities import AgentRun, Briefing, DataProvenance, Event, Evidence, Signal, SignalReview


class BackendRepository(Protocol):
    def get_meta(self) -> DataProvenance: ...

    def list_events(
        self,
        *,
        instrument_type: str | None = None,
        asset: str | None = None,
        published_after: str | None = None,
    ) -> tuple[tuple[Event, tuple[str, ...]], ...]: ...

    def get_event(self, event_id: str) -> tuple[Event, tuple[str, ...]]: ...

    def get_watchlist(self) -> Watchlist: ...

    def list_signals(
        self,
        *,
        instrument_type: str | None = None,
        asset: str | None = None,
        published_after: str | None = None,
    ) -> tuple[Signal, ...]: ...

    def get_signal(self, signal_id: str) -> Signal: ...

    def get_signal_evidence(self, signal_id: str) -> tuple[Evidence, ...]: ...

    def list_signal_reviews(self, signal_id: str) -> tuple[SignalReview, ...]: ...

    def create_signal_review(
        self,
        signal_id: str,
        request: ReviewRequest,
        *,
        idempotency_key: str,
    ) -> tuple[SignalReview, ...]: ...

    def create_briefing(
        self,
        request: BriefingRequest,
        *,
        idempotency_key: str,
        executive_summary: str,
    ) -> Briefing: ...

    def get_briefing(self, briefing_id: str) -> Briefing: ...

    def create_analysis_run(
        self,
        request: AnalysisRequest,
        *,
        idempotency_key: str,
        model_name: str,
        prompt_version: str,
    ) -> AgentRun: ...

    def get_analysis_run(self, run_id: str) -> AgentRun: ...

    def get_run_steps(self, run_id: str) -> tuple[AgentRunStep, ...]: ...
