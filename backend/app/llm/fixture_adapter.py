"""Deterministic fixture-backed LLM adapter."""

from __future__ import annotations

from app.contracts.entities import Signal
from app.llm.base import LLMAdapter


class FixtureLLMAdapter(LLMAdapter):
    """Return deterministic texts derived from fixture contracts."""

    def summarize_signal(self, signal: Signal) -> str:
        return signal.thesis or (
            f"Senal {signal.impact.value} para {signal.asset.symbol} con "
            f"confianza {signal.confidence:.2f}."
        )

    def build_briefing_summary(self, signals: tuple[Signal, ...]) -> str:
        if not signals:
            return "No se seleccionaron senales para este briefing."
        highest_confidence = max(signals, key=lambda signal: signal.confidence)
        return (
            "Resumen generado en modo fixture. "
            f"La senal prioritaria actual es {highest_confidence.asset.symbol} "
            f"con impacto {highest_confidence.impact.value}."
        )
