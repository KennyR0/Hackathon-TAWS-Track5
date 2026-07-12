"""LLM adapter interfaces and structured internal outputs."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.entities import Signal


class SignalAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    thesis: str
    assumptions: list[str] = Field(min_length=1)
    invalidation_conditions: list[str] = Field(min_length=1)
    suggested_research_actions: list[str] = Field(min_length=1)
    analyst_summary: str


class BriefingSummaryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    executive_summary: str


class LLMAdapter(Protocol):
    """Minimal interface for backend-facing LLM adapters."""

    def analyze_signal(self, signal: Signal) -> SignalAnalysisOutput: ...

    def build_briefing(
        self,
        signals: tuple[Signal, ...],
        *,
        warnings: tuple[str, ...] = (),
    ) -> BriefingSummaryOutput: ...
