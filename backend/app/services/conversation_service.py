"""Conversation application service."""

from __future__ import annotations

from app.contracts.entities import DataProvenance
from app.models.conversations import Conversation, ConversationMessage
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.fixture_repository import FixtureRepository


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        data_repository: FixtureRepository | None = None,
    ) -> None:
        self._repository = repository
        self._data_repository = data_repository

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


__all__ = ["ConversationService"]
