from __future__ import annotations

from app.repositories.conversation_repository import InMemoryConversationRepository
from app.services.conversation_service import ConversationService


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
