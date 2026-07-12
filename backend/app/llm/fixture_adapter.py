"""Deterministic fixture-backed LLM adapter."""

from __future__ import annotations

from app.contracts.entities import Signal
from app.llm.base import BriefingSummaryOutput, LLMAdapter, SignalAnalysisOutput


class FixtureLLMAdapter(LLMAdapter):
    """Return deterministic texts derived from fixture contracts."""

    def analyze_signal(self, signal: Signal) -> SignalAnalysisOutput:
        thesis = signal.thesis or (
            f"Senal {signal.impact.value} para {signal.asset.symbol} con "
            f"confianza {signal.confidence:.2f}."
        )
        return SignalAnalysisOutput(
            thesis=thesis,
            assumptions=list(signal.assumptions or ("Confirmar la noticia con sus fuentes originales.",)),
            invalidation_conditions=list(
                signal.invalidation_conditions or ("La evidencia de mercado no confirma la tesis.",)
            ),
            suggested_research_actions=list(
                signal.suggested_research_actions or ("Revisar la evidencia de respaldo.",)
            ),
            analyst_summary=thesis,
        )

    def build_briefing(
        self,
        signals: tuple[Signal, ...],
        *,
        warnings: tuple[str, ...] = (),
    ) -> BriefingSummaryOutput:
        if not signals:
            return BriefingSummaryOutput(
                executive_summary="No se seleccionaron senales elegibles para este briefing."
            )
        highest_confidence = max(signals, key=lambda signal: signal.confidence)
        summary = (
            "Resumen generado en modo fixture. "
            f"La senal prioritaria actual es {highest_confidence.asset.symbol} "
            f"con impacto {highest_confidence.impact.value}."
        )
        if warnings:
            summary = f"{summary} Advertencias: {' | '.join(warnings)}."
        return BriefingSummaryOutput(executive_summary=summary)
