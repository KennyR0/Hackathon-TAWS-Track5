"""LLM adapter interfaces and structured internal outputs."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.entities import DataMode, Signal


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


class ConversationAssistantOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    provider: str
    model_name: str
    data_mode: DataMode
    provider_conversation_id: str | None = None
    response_id: str | None = None


class LLMAdapter(Protocol):
    """Minimal interface for backend-facing LLM adapters."""

    def analyze_signal(self, signal: Signal) -> SignalAnalysisOutput: ...

    def build_briefing(
        self,
        signals: tuple[Signal, ...],
        *,
        warnings: tuple[str, ...] = (),
    ) -> BriefingSummaryOutput: ...

    def create_conversation(self) -> str | None: ...

    def answer_conversation(
        self,
        *,
        prompt: str,
        instructions: str,
        fallback_content: str,
        provider_conversation_id: str | None,
    ) -> ConversationAssistantOutput: ...
