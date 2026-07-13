"""Conversation persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from supabase import Client

from app.contracts.entities import allow_internal_field_names
from app.models.conversations import Conversation, ConversationMessage


def _is_missing_schema_column_error(error: Exception, column: str) -> bool:
    message = str(error)
    return (
        "PGRST204" in message
        and f"'{column}' column" in message
        and "'conversations'" in message
    )


class ConversationRepository(Protocol):
    def create(
        self,
        *,
        organization_id: str,
        user_id: str,
        watchlist_id: str | None = None,
    ) -> Conversation: ...

    def get(self, conversation_id: str) -> Conversation | None: ...

    def add_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> ConversationMessage: ...

    def get_provider_conversation_id(self, conversation_id: str) -> str | None: ...

    def set_provider_conversation_id(
        self,
        conversation_id: str,
        provider_conversation_id: str,
    ) -> None: ...

    def update_context(
        self,
        conversation_id: str,
        *,
        summary: str | None = None,
        active_event_id: str | None = None,
        active_signal_id: str | None = None,
        active_instrument_symbol: str | None = None,
        clear_active_signal: bool = False,
        last_run_id: str | None = None,
    ) -> Conversation | None: ...


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[ConversationMessage]] = {}
        self._provider_conversation_ids: dict[str, str] = {}

    def create(
        self,
        *,
        organization_id: str,
        user_id: str,
        watchlist_id: str | None = None,
    ) -> Conversation:
        now = datetime.now(UTC)
        conversation_id = f"conv_{uuid4().hex[:12]}"
        with allow_internal_field_names():
            conversation = Conversation(
                id=conversation_id,
                organization_id=organization_id,
                user_id=user_id,
                watchlist_id=watchlist_id,
                created_at=now,
                updated_at=now,
            )
        self._conversations[conversation_id] = conversation
        self._messages[conversation_id] = []
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            return None
        return conversation.model_copy(
            update={"messages": tuple(self._messages.get(conversation_id, []))}
        )

    def add_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> ConversationMessage:
        if conversation_id not in self._conversations:
            raise KeyError(conversation_id)
        with allow_internal_field_names():
            message = ConversationMessage(
                id=f"msg_{uuid4().hex[:12]}",
                conversation_id=conversation_id,
                role=role,  # type: ignore[arg-type]
                content=content,
                metadata=metadata or {},
                created_at=datetime.now(UTC),
            )
        self._messages.setdefault(conversation_id, []).append(message)
        existing = self._conversations[conversation_id]
        self._conversations[conversation_id] = existing.model_copy(
            update={"updated_at": message.created_at}
        )
        return message

    def get_provider_conversation_id(self, conversation_id: str) -> str | None:
        if conversation_id not in self._conversations:
            raise KeyError(conversation_id)
        return self._provider_conversation_ids.get(conversation_id)

    def set_provider_conversation_id(
        self,
        conversation_id: str,
        provider_conversation_id: str,
    ) -> None:
        if conversation_id not in self._conversations:
            raise KeyError(conversation_id)
        self._provider_conversation_ids[conversation_id] = provider_conversation_id

    def update_context(
        self,
        conversation_id: str,
        *,
        summary: str | None = None,
        active_event_id: str | None = None,
        active_signal_id: str | None = None,
        active_instrument_symbol: str | None = None,
        clear_active_signal: bool = False,
        last_run_id: str | None = None,
    ) -> Conversation | None:
        existing = self._conversations.get(conversation_id)
        if existing is None:
            return None
        updates: dict[str, object] = {"updated_at": datetime.now(UTC)}
        if summary is not None:
            updates["summary"] = summary
        if active_event_id is not None:
            updates["active_event_id"] = active_event_id
        if clear_active_signal:
            updates["active_signal_id"] = None
        elif active_signal_id is not None:
            updates["active_signal_id"] = active_signal_id
        if active_instrument_symbol is not None:
            updates["active_instrument_symbol"] = active_instrument_symbol
        if last_run_id is not None:
            updates["last_run_id"] = last_run_id
        updated = existing.model_copy(update=updates)
        self._conversations[conversation_id] = updated
        return self.get(conversation_id)


class SupabaseConversationRepository:
    def __init__(self, client: Client) -> None:
        self._client = client

    def create(
        self,
        *,
        organization_id: str,
        user_id: str,
        watchlist_id: str | None = None,
    ) -> Conversation:
        conversation_id = f"conv_{uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        row = {
            "id": conversation_id,
            "organization_id": organization_id,
            "user_id": user_id,
            "watchlist_id": watchlist_id,
            "created_at": now,
            "updated_at": now,
        }
        self._client.table("conversations").insert(row).execute()
        with allow_internal_field_names():
            return Conversation(
                id=conversation_id,
                organization_id=organization_id,
                user_id=user_id,
                watchlist_id=watchlist_id,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )

    def get(self, conversation_id: str) -> Conversation | None:
        rows = (
            self._client.table("conversations")
            .select("*")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        row = rows[0]
        message_rows = (
            self._client.table("conversation_messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
            .data
            or []
        )
        with allow_internal_field_names():
            messages = tuple(
                ConversationMessage(
                    id=item["id"],
                    conversation_id=item["conversation_id"],
                    role=item["role"],
                    content=item["content"],
                    metadata=item.get("metadata") or {},
                    created_at=item["created_at"],
                )
                for item in message_rows
            )
            return Conversation(
                id=row["id"],
                organization_id=row["organization_id"],
                user_id=row["user_id"],
                watchlist_id=row.get("watchlist_id"),
                active_event_id=row.get("active_event_id"),
                active_signal_id=row.get("active_signal_id"),
                active_instrument_symbol=row.get("active_instrument_symbol"),
                summary=row.get("summary"),
                last_run_id=row.get("last_run_id"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                messages=messages,
            )

    def add_message(
        self,
        conversation_id: str,
        *,
        role: str,
        content: str,
        metadata: dict[str, object] | None = None,
    ) -> ConversationMessage:
        message_id = f"msg_{uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()
        self._client.table("conversation_messages").insert(
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "created_at": now,
            }
        ).execute()
        self._client.table("conversations").update({"updated_at": now}).eq(
            "id", conversation_id
        ).execute()
        with allow_internal_field_names():
            return ConversationMessage(
                id=message_id,
                conversation_id=conversation_id,
                role=role,  # type: ignore[arg-type]
                content=content,
                metadata=metadata or {},
                created_at=datetime.fromisoformat(now),
            )

    def get_provider_conversation_id(self, conversation_id: str) -> str | None:
        rows = (
            self._client.table("conversations")
            .select("openai_conversation_id")
            .eq("id", conversation_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            raise KeyError(conversation_id)
        value = rows[0].get("openai_conversation_id")
        return str(value) if value else None

    def set_provider_conversation_id(
        self,
        conversation_id: str,
        provider_conversation_id: str,
    ) -> None:
        self.get_provider_conversation_id(conversation_id)
        (
            self._client.table("conversations")
            .update({"openai_conversation_id": provider_conversation_id})
            .eq("id", conversation_id)
            .execute()
        )

    def update_context(
        self,
        conversation_id: str,
        *,
        summary: str | None = None,
        active_event_id: str | None = None,
        active_signal_id: str | None = None,
        active_instrument_symbol: str | None = None,
        clear_active_signal: bool = False,
        last_run_id: str | None = None,
    ) -> Conversation | None:
        updates: dict[str, object] = {"updated_at": datetime.now(UTC).isoformat()}
        if summary is not None:
            updates["summary"] = summary
        if active_event_id is not None:
            updates["active_event_id"] = active_event_id
        if clear_active_signal:
            updates["active_signal_id"] = None
        elif active_signal_id is not None:
            updates["active_signal_id"] = active_signal_id
        if active_instrument_symbol is not None:
            updates["active_instrument_symbol"] = active_instrument_symbol
        if last_run_id is not None:
            updates["last_run_id"] = last_run_id
        try:
            self._client.table("conversations").update(updates).eq(
                "id", conversation_id
            ).execute()
        except Exception as error:
            if "active_instrument_symbol" not in updates or not _is_missing_schema_column_error(
                error, "active_instrument_symbol"
            ):
                raise
            compatible_updates = {
                key: value
                for key, value in updates.items()
                if key != "active_instrument_symbol"
            }
            self._client.table("conversations").update(compatible_updates).eq(
                "id", conversation_id
            ).execute()
        return self.get(conversation_id)


__all__ = [
    "ConversationRepository",
    "InMemoryConversationRepository",
    "SupabaseConversationRepository",
]
