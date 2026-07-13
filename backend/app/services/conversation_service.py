"""Conversation application service."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.contracts.api import ConversationAssetContext, ConversationTurn, MarketQuote
from app.contracts.entities import (
    DataMode,
    DataProvenance,
    Evidence,
    Signal,
    allow_internal_field_names,
)
from app.llm.base import ConversationAssistantOutput, LLMAdapter
from app.market_universe import UniverseInstrument
from app.models.conversations import Conversation, ConversationMessage
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.fixture_repository import FixtureRepository
from app.services.differentiator_service import DifferentiatorService
from app.services.instrument_service import InstrumentService


@dataclass(frozen=True)
class ResolvedAssetContext:
    instrument: UniverseInstrument | None
    signal: Signal | None
    quote: MarketQuote | None
    unsupported_symbol: str | None = None
    quote_warning: str | None = None

    @property
    def coverage(self) -> str:
        if self.unsupported_symbol:
            return "unsupported"
        return "signal" if self.signal is not None else "quote_only"


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        data_repository: FixtureRepository | None = None,
        llm_adapter: LLMAdapter | None = None,
        instrument_service: InstrumentService | None = None,
    ) -> None:
        self._repository = repository
        self._data_repository = data_repository
        self._llm_adapter = llm_adapter
        self._instrument_service = instrument_service

    @property
    def meta(self) -> DataProvenance:
        if self._data_repository is None:
            raise RuntimeError("ConversationService meta requires a data repository")
        return self._data_repository.get_meta()

    def create_conversation(
        self,
        *,
        organization_id: str,
        user_id: str,
        watchlist_id: str | None = None,
    ) -> Conversation:
        return self._repository.create(
            organization_id=organization_id,
            user_id=user_id,
            watchlist_id=watchlist_id,
        )

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._repository.get(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> ConversationMessage:
        return self._repository.add_message(
            conversation_id,
            role=role,
            content=content,
            metadata=metadata,
        )

    def update_summary(self, conversation_id: str, summary: str) -> Conversation | None:
        return self._repository.update_context(conversation_id, summary=summary)

    def link_run(self, conversation_id: str, run_id: str) -> Conversation | None:
        return self._repository.update_context(conversation_id, last_run_id=run_id)

    def respond(self, conversation_id: str, content: str) -> ConversationTurn:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise KeyError(conversation_id)
        asset_context = self._resolve_asset_context(conversation, content)
        user_message = self.add_message(
            conversation_id,
            role="user",
            content=content,
            metadata={"source": "assistant_page", "requiresHumanReview": True},
        )
        signal = asset_context.signal
        evidence_ids = tuple(item.id for item in self._evidence_for(signal))
        if asset_context.instrument is not None:
            self._repository.update_context(
                conversation_id,
                active_signal_id=signal.id if signal is not None else None,
                active_instrument_symbol=asset_context.instrument.symbol,
                clear_active_signal=signal is None,
            )
        instructions = self._build_instructions(asset_context)
        fallback_content = self._build_fallback(asset_context, evidence_ids)
        output, used_fallback, provider_warning = self._generate_answer(
            conversation_id=conversation_id,
            prompt=content,
            instructions=instructions,
            fallback_content=fallback_content,
        )
        warning = self._merge_warnings(asset_context.quote_warning, provider_warning)
        response_context = self._response_context(asset_context)
        metadata: dict[str, object] = {
            "provider": output.provider,
            "model": output.model_name,
            "dataMode": output.data_mode.value,
            "evidenceIds": list(evidence_ids),
            "requiresHumanReview": True,
            "usedFallback": used_fallback,
            "assetSymbol": response_context.symbol,
            "assetName": response_context.name,
            "coverage": response_context.coverage,
            "quoteDataMode": response_context.data_mode,
        }
        if signal is not None:
            metadata["signalId"] = signal.id
        if output.response_id:
            metadata["openaiResponseId"] = output.response_id
        if warning:
            metadata["warning"] = warning
        assistant_message = self.add_message(
            conversation_id,
            role="assistant",
            content=output.content,
            metadata=metadata,
        )
        with allow_internal_field_names():
            return ConversationTurn(
                user_message=user_message,
                assistant_message=assistant_message,
                used_fallback=used_fallback,
                warning=warning,
                context=response_context,
            )

    def _generate_answer(
        self,
        *,
        conversation_id: str,
        prompt: str,
        instructions: str,
        fallback_content: str,
    ) -> tuple[ConversationAssistantOutput, bool, str | None]:
        if self._llm_adapter is None:
            return self._fallback_output(fallback_content), True, "Asistente no configurado."
        try:
            provider_conversation_id = self._repository.get_provider_conversation_id(
                conversation_id
            )
            if provider_conversation_id is None:
                provider_conversation_id = self._llm_adapter.create_conversation()
                if provider_conversation_id:
                    self._repository.set_provider_conversation_id(
                        conversation_id,
                        provider_conversation_id,
                    )
            output = self._llm_adapter.answer_conversation(
                prompt=prompt,
                instructions=instructions,
                fallback_content=fallback_content,
                provider_conversation_id=provider_conversation_id,
            )
            used_fallback = output.data_mode != DataMode.LIVE
            warning = "Respuesta determinística en modo fixture." if used_fallback else None
            return output, used_fallback, warning
        except Exception:
            warning = "OpenAI no estuvo disponible; se mostró un resumen determinístico."
            return self._fallback_output(fallback_content), True, warning

    @staticmethod
    def _fallback_output(content: str) -> ConversationAssistantOutput:
        return ConversationAssistantOutput(
            content=content,
            provider="nexomercado_fallback",
            model_name="deterministic",
            data_mode=DataMode.FALLBACK,
        )

    def _resolve_asset_context(
        self,
        conversation: Conversation,
        content: str,
    ) -> ResolvedAssetContext:
        if self._instrument_service is None:
            signal = self._active_or_default_signal(conversation)
            return ResolvedAssetContext(instrument=None, signal=signal, quote=None)

        instrument = self._instrument_service.resolve_mention(content)
        unsupported_symbol = self._instrument_service.detect_unsupported_symbol(content)
        if instrument is None and unsupported_symbol:
            return ResolvedAssetContext(
                instrument=None,
                signal=None,
                quote=None,
                unsupported_symbol=unsupported_symbol,
            )
        if instrument is None:
            instrument = self._instrument_service.get_instrument(
                conversation.active_instrument_symbol
            )
        if instrument is None and conversation.active_signal_id:
            active_signal = self._signal_by_id(conversation.active_signal_id)
            if active_signal is not None:
                instrument = self._instrument_service.get_instrument(
                    active_signal.asset.symbol
                )
        if instrument is None:
            instrument = self._instrument_service.get_instrument("AAPL")

        signal = self._signal_for_symbol(instrument.symbol) if instrument else None
        quote, quote_warning = self._quote_for(instrument) if signal is None else (None, None)
        return ResolvedAssetContext(
            instrument=instrument,
            signal=signal,
            quote=quote,
            quote_warning=quote_warning,
        )

    def _active_or_default_signal(self, conversation: Conversation) -> Signal | None:
        if conversation.active_signal_id:
            active = self._signal_by_id(conversation.active_signal_id)
            if active is not None:
                return active
        signals = self._data_repository.list_signals() if self._data_repository else ()
        return next(
            (item for item in signals if item.asset.symbol.upper() == "AAPL"),
            signals[0] if signals else None,
        )

    def _signal_by_id(self, signal_id: str) -> Signal | None:
        if self._data_repository is None:
            return None
        return next(
            (item for item in self._data_repository.list_signals() if item.id == signal_id),
            None,
        )

    def _signal_for_symbol(self, symbol: str) -> Signal | None:
        if self._data_repository is None:
            return None
        return next(
            (
                item
                for item in self._data_repository.list_signals()
                if item.asset.symbol.upper() == symbol.upper()
            ),
            None,
        )

    def _quote_for(
        self,
        instrument: UniverseInstrument | None,
    ) -> tuple[MarketQuote | None, str | None]:
        if instrument is None or self._instrument_service is None:
            return None, None
        try:
            response = self._instrument_service.list_quotes((instrument.symbol,))
            quote = response.data[0] if response.data else None
            warning = "; ".join(response.meta.warnings) if response.meta.warnings else None
            return quote, warning
        except Exception:
            return None, "La cotización no estuvo disponible; no se inventaron cifras."

    def _evidence_for(self, signal: Signal | None) -> tuple[Evidence, ...]:
        if self._data_repository is None or signal is None:
            return ()
        return self._data_repository.get_signal_evidence(signal.id)

    def _build_instructions(self, asset_context: ResolvedAssetContext) -> str:
        signal = asset_context.signal
        evidence = self._evidence_for(signal)
        context: dict[str, object] = {
            "instrument": None,
            "coverage": asset_context.coverage,
            "unsupportedSymbol": asset_context.unsupported_symbol,
            "quote": None,
            "signal": None,
            "event": None,
            "evidence": [],
            "ecuadorSnapshots": [],
        }
        if asset_context.instrument is not None:
            context["instrument"] = asset_context.instrument.model_dump(
                mode="json", by_alias=True
            )
        if asset_context.quote is not None:
            context["quote"] = asset_context.quote.model_dump(mode="json", by_alias=True)
        if self._data_repository is not None:
            snapshots = DifferentiatorService(
                self._data_repository
            ).list_ecuador_snapshots().data
            context["ecuadorSnapshots"] = [
                {
                    "id": item.id,
                    "title": item.title,
                    "summary": item.summary,
                    "sourceName": item.source_name,
                    "sourceUrl": str(item.source_url),
                    "contentHash": item.content_hash,
                }
                for item in snapshots
            ]
        if signal is not None and self._data_repository is not None:
            event, _ = self._data_repository.get_event(signal.event_id)
            context["signal"] = signal.model_dump(mode="json", by_alias=True)
            context["event"] = event.model_dump(mode="json", by_alias=True)
            context["evidence"] = [
                item.model_dump(mode="json", by_alias=True) for item in evidence
            ]
        serialized = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
        return (
            "Eres la interfaz conversacional del Analista de Coyuntura de Mercados IA. "
            "Responde en español y usa exclusivamente el contexto JSON entregado. "
            "Cuando coverage sea signal, cita cada afirmación financiera con su "
            "identificador [evidenceId]. "
            "Si coverage es quote_only, limita la respuesta a la ficha y cotización entregadas "
            "identificando proveedor y modo, sin exigir evidenceId, y aclara que NexoMercado "
            "no tiene una señal respaldada para ese instrumento. "
            "Si coverage es unsupported, indica que el símbolo no pertenece al universo "
            "de 25 instrumentos. "
            "No inventes cifras, fuentes ni relaciones causales. No recomiendes comprar o vender, "
            "no prometas rendimientos y termina recordando que requiere revisión humana. "
            f"Contexto verificable: {serialized}"
        )

    @staticmethod
    def _build_fallback(
        asset_context: ResolvedAssetContext,
        evidence_ids: tuple[str, ...],
    ) -> str:
        signal = asset_context.signal
        if asset_context.unsupported_symbol:
            return (
                f"{asset_context.unsupported_symbol} no forma parte del universo productivo "
                "de 25 instrumentos de NexoMercado. No se usó AAPL como sustituto y no se "
                "inventaron datos. Requiere revisión humana."
            )
        if signal is None and asset_context.instrument is not None:
            instrument = asset_context.instrument
            quote = asset_context.quote
            quote_text = "La cotización verificable no está disponible."
            if quote is not None and quote.price is not None:
                quote_text = (
                    f"Cotización verificable: {quote.price:g} {quote.currency}, "
                    f"proveedor {quote.provider}, modo {quote.data_mode.value}."
                )
            return (
                f"{instrument.name} ({instrument.symbol}) está incluido en el catálogo. "
                f"{quote_text} NexoMercado todavía no tiene una señal respaldada por evidencia "
                "para este instrumento. No constituye recomendación de compra o venta y "
                "requiere revisión humana."
            )
        if signal is None:
            return "No hay contexto verificable disponible. Requiere revisión humana."
        citations = " ".join(f"[{item}]" for item in evidence_ids) or "sin evidencia vinculada"
        thesis = signal.thesis or "La señal no tiene una tesis concluyente."
        return (
            f"Resumen verificable de {signal.asset.symbol}: {thesis} "
            f"Impacto {signal.impact.value} y confianza {signal.confidence:.0%}. "
            f"Evidencia: {citations}. No constituye recomendación de compra o venta "
            "y requiere revisión humana."
        )

    @staticmethod
    def _response_context(asset_context: ResolvedAssetContext) -> ConversationAssetContext:
        instrument = asset_context.instrument
        signal = asset_context.signal
        data_mode = asset_context.quote.data_mode.value if asset_context.quote else None
        if asset_context.quote_warning and data_mode is None:
            data_mode = "fallback"
        with allow_internal_field_names():
            return ConversationAssetContext(
                symbol=(
                    instrument.symbol
                    if instrument
                    else asset_context.unsupported_symbol
                    or (signal.asset.symbol if signal else "N/A")
                ),
                name=(
                    instrument.name
                    if instrument
                    else signal.asset.name
                    if signal
                    else "Instrumento no cubierto"
                ),
                coverage=asset_context.coverage,  # type: ignore[arg-type]
                data_mode=data_mode,  # type: ignore[arg-type]
            )

    @staticmethod
    def _merge_warnings(*warnings: str | None) -> str | None:
        unique = tuple(dict.fromkeys(item for item in warnings if item))
        return " ".join(unique) or None


__all__ = ["ConversationService", "ResolvedAssetContext"]
