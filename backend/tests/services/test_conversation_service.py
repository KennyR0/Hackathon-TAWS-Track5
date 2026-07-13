from __future__ import annotations

from pathlib import Path

from app.contracts.entities import DataMode
from app.llm.base import ConversationAssistantOutput
from app.market_universe import load_market_universe
from app.providers.base import ProviderProbeResult
from app.providers.fixture_provider import FixtureProvider
from app.repositories.conversation_repository import InMemoryConversationRepository
from app.repositories.fixture_repository import FixtureRepository
from app.services.conversation_service import ConversationService
from app.services.instrument_service import InstrumentService


class TrackingConversationAdapter:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.create_calls = 0
        self.provider_ids: list[str | None] = []
        self.instructions: list[str] = []

    def create_conversation(self) -> str:
        self.create_calls += 1
        return "conv_openai_test"

    def answer_conversation(
        self,
        *,
        prompt: str,
        instructions: str,
        fallback_content: str,
        provider_conversation_id: str | None,
    ) -> ConversationAssistantOutput:
        _ = (prompt, fallback_content)
        self.instructions.append(instructions)
        self.provider_ids.append(provider_conversation_id)
        if self.should_fail:
            raise RuntimeError("provider unavailable")
        return ConversationAssistantOutput(
            content="Respuesta sustentada [evd_aapl_source_apple]. Requiere revisión humana.",
            provider="openai",
            model_name="gpt-5.4",
            data_mode=DataMode.LIVE,
            provider_conversation_id=provider_conversation_id,
            response_id="resp_test_001",
        )


def _data_repository() -> FixtureRepository:
    bundle = Path(__file__).resolve().parents[3] / "data/fixtures/v1/phase0_bundle.json"
    return FixtureRepository(FixtureProvider(bundle))


class QuoteRuntimeStub:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def collect_quotes(self, instruments) -> dict[str, ProviderProbeResult]:
        if self.should_fail:
            raise RuntimeError("quote provider unavailable")
        return {
            item.symbol: ProviderProbeResult(
                provider="quote_stub",
                data_mode="live",
                ok=True,
                warnings=(),
                payload={"close": 100, "previousClose": 98},
            )
            for item in instruments
        }


def _instrument_service(*, quote_failure: bool = False) -> InstrumentService:
    return InstrumentService(
        load_market_universe(),
        QuoteRuntimeStub(should_fail=quote_failure),  # type: ignore[arg-type]
    )


def test_conversation_message_order_and_persistence() -> None:
    repo = InMemoryConversationRepository()
    service = ConversationService(repo)
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )
    service.add_message(conversation.id, role="user", content="Hola")
    service.add_message(conversation.id, role="assistant", content="Contexto cargado")
    loaded = service.get_conversation(conversation.id)
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert loaded.messages[0].role == "user"
    assert loaded.messages[1].role == "assistant"


def test_link_run_updates_conversation() -> None:
    repo = InMemoryConversationRepository()
    service = ConversationService(repo)
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )
    updated = service.link_run(conversation.id, "run_test_001")
    assert updated is not None
    assert updated.last_run_id == "run_test_001"


def test_conversation_reuses_provider_state_and_persists_turns() -> None:
    repository = InMemoryConversationRepository()
    adapter = TrackingConversationAdapter()
    service = ConversationService(repository, _data_repository(), adapter)  # type: ignore[arg-type]
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )

    first = service.respond(conversation.id, "Explica AAPL con evidencia.")
    second = service.respond(conversation.id, "¿Qué podría invalidar esa tesis?")
    loaded = service.get_conversation(conversation.id)

    assert adapter.create_calls == 1
    assert adapter.provider_ids == ["conv_openai_test", "conv_openai_test"]
    assert first.used_fallback is False
    assert second.assistant_message.metadata["dataMode"] == "live"
    assert loaded is not None
    assert [item.role for item in loaded.messages] == ["user", "assistant", "user", "assistant"]


def test_conversation_falls_back_with_evidence_when_provider_fails() -> None:
    repository = InMemoryConversationRepository()
    adapter = TrackingConversationAdapter(should_fail=True)
    service = ConversationService(repository, _data_repository(), adapter)  # type: ignore[arg-type]
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )

    turn = service.respond(conversation.id, "Resume AAPL.")

    assert turn.used_fallback is True
    assert turn.warning is not None
    assert "[evd_" in turn.assistant_message.content
    assert turn.assistant_message.metadata["dataMode"] == "fallback"


def test_explicit_bitcoin_overrides_active_aapl_and_persists_for_follow_up() -> None:
    repository = InMemoryConversationRepository()
    adapter = TrackingConversationAdapter()
    service = ConversationService(
        repository,
        _data_repository(),
        adapter,  # type: ignore[arg-type]
        _instrument_service(),
    )
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )

    service.respond(conversation.id, "Explica AAPL")
    bitcoin_turn = service.respond(conversation.id, "Ahora explica bitcoin")
    follow_up = service.respond(conversation.id, "¿Qué podría invalidar esa tesis?")
    loaded = service.get_conversation(conversation.id)

    assert bitcoin_turn.context.symbol == "BTC-USD"
    assert bitcoin_turn.context.coverage == "signal"
    assert follow_up.context.symbol == "BTC-USD"
    assert '"symbol":"BTC-USD"' in adapter.instructions[-1]
    assert loaded is not None
    assert loaded.active_instrument_symbol == "BTC-USD"
    assert loaded.active_signal_id == "sig_btc_uncertain"


def test_quote_only_asset_clears_previous_signal_without_inventing_evidence() -> None:
    repository = InMemoryConversationRepository()
    adapter = TrackingConversationAdapter(should_fail=True)
    service = ConversationService(
        repository,
        _data_repository(),
        adapter,  # type: ignore[arg-type]
        _instrument_service(),
    )
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )

    service.respond(conversation.id, "Explica AAPL")
    turn = service.respond(conversation.id, "Ahora explícame Microsoft")
    loaded = service.get_conversation(conversation.id)

    assert turn.context.symbol == "MSFT"
    assert turn.context.coverage == "quote_only"
    assert turn.context.data_mode == "live"
    assert turn.assistant_message.metadata["evidenceIds"] == []
    assert "todavía no tiene una señal" in turn.assistant_message.content
    assert loaded is not None
    assert loaded.active_instrument_symbol == "MSFT"
    assert loaded.active_signal_id is None


def test_unsupported_symbol_does_not_silently_fall_back_to_aapl() -> None:
    repository = InMemoryConversationRepository()
    adapter = TrackingConversationAdapter(should_fail=True)
    service = ConversationService(
        repository,
        _data_repository(),
        adapter,  # type: ignore[arg-type]
        _instrument_service(),
    )
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )

    turn = service.respond(conversation.id, "Explica SOL con evidencia")

    assert turn.context.symbol == "SOL"
    assert turn.context.coverage == "unsupported"
    assert turn.assistant_message.metadata["evidenceIds"] == []
    assert "No se usó AAPL como sustituto" in turn.assistant_message.content


def test_quote_failure_is_labeled_and_never_fabricates_a_price() -> None:
    repository = InMemoryConversationRepository()
    adapter = TrackingConversationAdapter(should_fail=True)
    service = ConversationService(
        repository,
        _data_repository(),
        adapter,  # type: ignore[arg-type]
        _instrument_service(quote_failure=True),
    )
    conversation = service.create_conversation(
        organization_id="org_demo",
        user_id="usr_analista_demo",
    )

    turn = service.respond(conversation.id, "Explica MSFT")

    assert turn.context.data_mode == "fallback"
    assert turn.warning is not None
    assert "cotización verificable no está disponible" in turn.assistant_message.content
