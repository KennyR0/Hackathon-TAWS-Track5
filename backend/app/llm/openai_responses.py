"""OpenAI Responses API adapter."""

from __future__ import annotations

from openai import OpenAI

from app.contracts.entities import Signal
from app.llm.base import LLMAdapter
from app.openai_client import build_openai_client, build_responses_request


class OpenAIResponsesAdapter(LLMAdapter):
    """Use OpenAI Responses API for text generation."""

    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client or build_openai_client()

    def summarize_signal(self, signal: Signal) -> str:
        prompt = (
            "Resume con prudencia una senal financiera. "
            f"Activo: {signal.asset.symbol}. "
            f"Impacto: {signal.impact.value}. "
            f"Confianza: {signal.confidence:.2f}. "
            f"Tesis: {signal.thesis or 'Sin tesis disponible.'}"
        )
        response = self._client.responses.create(
            **build_responses_request(
                prompt,
                system_prompt=(
                    "Eres un analista financiero prudente. "
                    "No recomiendes comprar ni vender. "
                    "No prometas rendimiento."
                ),
            )
        )
        return response.output_text

    def build_briefing_summary(self, signals: tuple[Signal, ...]) -> str:
        prompt = "Genera un briefing corto y prudente para estas senales:\n" + "\n".join(
            f"- {signal.asset.symbol}: {signal.impact.value}, confianza {signal.confidence:.2f}"
            for signal in signals
        )
        response = self._client.responses.create(
            **build_responses_request(
                prompt,
                system_prompt=(
                    "Redacta un resumen ejecutivo financiero con revision humana obligatoria."
                ),
            )
        )
        return response.output_text
