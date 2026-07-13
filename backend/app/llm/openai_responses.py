"""OpenAI Responses API adapter."""

from __future__ import annotations

import json

from openai import OpenAI

from app.config import OpenAIConfig, get_openai_config
from app.contracts.entities import DataMode, Signal
from app.llm.base import (
    BriefingSummaryOutput,
    ConversationAssistantOutput,
    LLMAdapter,
    SignalAnalysisOutput,
)
from app.openai_client import build_openai_client, build_responses_request


class OpenAIResponsesAdapter(LLMAdapter):
    """Use OpenAI Responses API for text generation."""

    def __init__(
        self,
        client: OpenAI | None = None,
        config: OpenAIConfig | None = None,
    ) -> None:
        self._config = config or get_openai_config()
        self._client = client or build_openai_client(self._config)

    def analyze_signal(self, signal: Signal) -> SignalAnalysisOutput:
        prompt = (
            "Analiza con prudencia una senal financiera y responde solo con JSON estructurado. "
            f"Activo: {signal.asset.symbol}. "
            f"Impacto: {signal.impact.value}. "
            f"Confianza: {signal.confidence:.2f}. "
            f"Tesis: {signal.thesis or 'Sin tesis disponible.'}"
        )
        fallback = SignalAnalysisOutput(
            thesis=signal.thesis
            or (
                f"Senal {signal.impact.value} para {signal.asset.symbol} "
                f"con confianza {signal.confidence:.2f}."
            ),
            assumptions=list(
                signal.assumptions or ("Confirmar la noticia con sus fuentes originales.",)
            ),
            invalidation_conditions=list(
                signal.invalidation_conditions or ("La evidencia de mercado no confirma la tesis.",)
            ),
            suggested_research_actions=list(
                signal.suggested_research_actions or ("Revisar la evidencia de respaldo.",)
            ),
            analyst_summary=signal.thesis
            or (
                f"Senal {signal.impact.value} para {signal.asset.symbol} "
                f"con confianza {signal.confidence:.2f}."
            ),
        )
        return self._parse_structured_output(
            prompt,
            model=SignalAnalysisOutput,
            schema_name="signal_analysis_output",
            fallback=fallback,
            system_prompt=(
                "Eres un analista financiero prudente. "
                "No recomiendes comprar ni vender. "
                "No prometas rendimiento. "
                "No inventes cifras ni identificadores."
            ),
        )

    def build_briefing(
        self,
        signals: tuple[Signal, ...],
        *,
        warnings: tuple[str, ...] = (),
    ) -> BriefingSummaryOutput:
        prompt = "Genera un briefing corto y prudente para estas senales:\n" + "\n".join(
            f"- {signal.asset.symbol}: {signal.impact.value}, confianza {signal.confidence:.2f}"
            for signal in signals
        )
        if warnings:
            prompt = f"{prompt}\nAdvertencias: {' | '.join(warnings)}"
        fallback = BriefingSummaryOutput(
            executive_summary=(
                "Resumen ejecutivo con revision humana obligatoria. "
                + (
                    "La senal mas relevante es "
                    f"{max(signals, key=lambda signal: signal.confidence).asset.symbol}."
                    if signals
                    else "No se encontraron senales elegibles."
                )
            )
        )
        return self._parse_structured_output(
            prompt,
            model=BriefingSummaryOutput,
            schema_name="briefing_summary_output",
            fallback=fallback,
            system_prompt=(
                "Redacta un resumen ejecutivo financiero con revision humana obligatoria. "
                "No uses lenguaje de compra, venta ni promesas de rendimiento."
            ),
        )

    def create_conversation(self) -> str | None:
        return self._client.conversations.create().id

    def answer_conversation(
        self,
        *,
        prompt: str,
        instructions: str,
        fallback_content: str,
        provider_conversation_id: str | None,
    ) -> ConversationAssistantOutput:
        _ = fallback_content
        if not provider_conversation_id:
            raise ValueError("OpenAI conversation ID is required")
        response = self._client.responses.create(
            model=self._config.model,
            conversation=provider_conversation_id,
            instructions=instructions,
            input=[{"role": "user", "content": prompt}],
            reasoning={"effort": self._config.reasoning_effort},
        )
        content = response.output_text.strip()
        if not content:
            raise ValueError("OpenAI returned an empty conversation response")
        return ConversationAssistantOutput(
            content=content,
            provider="openai",
            model_name=self._config.model,
            data_mode=DataMode.LIVE,
            provider_conversation_id=provider_conversation_id,
            response_id=response.id,
        )

    def _parse_structured_output(
        self,
        prompt: str,
        *,
        model: type[SignalAnalysisOutput] | type[BriefingSummaryOutput],
        schema_name: str,
        fallback: SignalAnalysisOutput | BriefingSummaryOutput,
        system_prompt: str,
    ) -> SignalAnalysisOutput | BriefingSummaryOutput:
        response = self._client.responses.create(
            **build_responses_request(
                prompt,
                system_prompt=system_prompt,
                text_format={
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": model.model_json_schema(),
                },
            )
        )
        try:
            return model.model_validate(json.loads(response.output_text))
        except (ValueError, TypeError):
            return fallback
