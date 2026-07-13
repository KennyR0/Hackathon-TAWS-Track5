"""Conversation domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contracts.entities import ContractModel, Identifier


class ConversationMessage(ContractModel):
    id: Identifier
    conversation_id: Identifier
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class Conversation(ContractModel):
    id: Identifier
    organization_id: Identifier
    user_id: Identifier
    watchlist_id: Identifier | None = None
    active_event_id: Identifier | None = None
    active_signal_id: Identifier | None = None
    active_instrument_symbol: str | None = None
    summary: str | None = None
    last_run_id: Identifier | None = None
    created_at: datetime
    updated_at: datetime
    messages: tuple[ConversationMessage, ...] = ()


__all__ = ["Conversation", "ConversationMessage"]
