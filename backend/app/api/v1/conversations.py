"""Conversation endpoints for assistant continuity."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUserDep, get_conversation_service
from app.contracts.api import (
    ConversationCreateRequest,
    ConversationMessageRequest,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationTurnResponse,
)
from app.contracts.entities import allow_internal_field_names
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["conversations"])
ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=201,
    operation_id="createConversation",
)
def create_conversation(
    request: ConversationCreateRequest,
    user: CurrentUserDep,
    service: ConversationServiceDep,
) -> ConversationResponse:
    conversation = service.create_conversation(
        organization_id=user.organization_id,
        user_id=user.id,
        watchlist_id=request.watchlist_id,
    )
    service.update_summary(
        conversation.id,
        "Conversacion de demo con contexto trazable del radar, senales y briefing.",
    )
    loaded = service.get_conversation(conversation.id)
    assert loaded is not None
    with allow_internal_field_names():
        return ConversationResponse(data=loaded, meta=service.meta)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    operation_id="getConversation",
)
def get_conversation(
    conversation_id: str,
    service: ConversationServiceDep,
) -> ConversationResponse:
    conversation = service.get_conversation(conversation_id)
    if conversation is None:
        raise KeyError(conversation_id)
    with allow_internal_field_names():
        return ConversationResponse(data=conversation, meta=service.meta)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessageResponse,
    status_code=201,
    operation_id="createConversationMessage",
)
def create_conversation_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    service: ConversationServiceDep,
) -> ConversationMessageResponse:
    message = service.add_message(
        conversation_id,
        role="user",
        content=request.content,
        metadata={"source": "assistant_page", "requiresHumanReview": True},
    )
    with allow_internal_field_names():
        return ConversationMessageResponse(data=message, meta=service.meta)


@router.post(
    "/conversations/{conversation_id}/responses",
    response_model=ConversationTurnResponse,
    status_code=201,
    operation_id="createConversationResponse",
)
def create_conversation_response(
    conversation_id: str,
    request: ConversationMessageRequest,
    service: ConversationServiceDep,
) -> ConversationTurnResponse:
    turn = service.respond(conversation_id, request.content)
    with allow_internal_field_names():
        return ConversationTurnResponse(data=turn, meta=service.meta)
