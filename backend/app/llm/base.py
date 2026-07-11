"""LLM adapter interfaces."""

from __future__ import annotations

from typing import Protocol

from app.contracts.entities import Signal


class LLMAdapter(Protocol):
    """Minimal interface for backend-facing LLM adapters."""

    def summarize_signal(self, signal: Signal) -> str: ...

    def build_briefing_summary(self, signals: tuple[Signal, ...]) -> str: ...
