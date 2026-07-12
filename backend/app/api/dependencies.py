"""Dependency providers for the NexoMercado HTTP API."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_market_provider_config, get_runtime_config, get_supabase_config
from app.llm.base import LLMAdapter
from app.llm.fixture_adapter import FixtureLLMAdapter
from app.llm.openai_responses import OpenAIResponsesAdapter
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService
from app.repositories.conversation_repository import (
    InMemoryConversationRepository,
    SupabaseConversationRepository,
)
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.supabase_repository import SupabaseRepository
from app.security.auth import (
    AppUserContext,
    extract_auth_user_id,
    get_auth_config,
    resolve_app_user,
)
from app.services.analysis_service import AnalysisService
from app.services.briefing_service import BriefingService
from app.services.conversation_service import ConversationService
from app.services.differentiator_service import DifferentiatorService
from app.services.event_service import EventService
from app.services.market_service import MarketService
from app.services.provider_demo_service import ProviderDemoService
from app.services.provider_runtime_service import (
    build_in_memory_provider_runtime,
    build_supabase_provider_runtime,
)
from app.services.review_service import ReviewService
from app.services.signal_service import SignalService
from app.supabase_client import create_supabase_client

_bearer = HTTPBearer(auto_error=False)
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


@lru_cache
def get_fixture_provider() -> FixtureProvider:
    runtime_config = get_runtime_config()
    return FixtureProvider(runtime_config.fixture_bundle_path)


@lru_cache
def get_repository() -> FixtureRepository:
    runtime_config = get_runtime_config()
    if runtime_config.repository_backend == "supabase":
        return SupabaseRepository(
            get_fixture_provider(),
            get_supabase_client(),
            get_market_data_runtime_service(),
        )
    return FixtureRepository(
        get_fixture_provider(),
        market_runtime=get_market_data_runtime_service(),
    )


@lru_cache
def get_supabase_client():
    return create_supabase_client(get_supabase_config())


@lru_cache
def get_in_memory_conversation_repository() -> InMemoryConversationRepository:
    return InMemoryConversationRepository()


def get_current_app_user(
    credentials: BearerCredentials,
) -> AppUserContext:
    config = get_auth_config()
    if not config.enabled:
        return AppUserContext(
            id="usr_analista_demo",
            organization_id="org_demo",
            role="analyst",
            display_name="Analista Demo",
            is_active=True,
        )
    auth_user_id = extract_auth_user_id(
        get_supabase_client(),
        credentials,
        config=config,
    )
    assert auth_user_id is not None
    return resolve_app_user(get_supabase_client(), auth_user_id)


CurrentUserDep = Annotated[AppUserContext, Depends(get_current_app_user)]


def get_scoped_repository(user: AppUserContext) -> FixtureRepository:
    runtime_config = get_runtime_config()
    if runtime_config.repository_backend == "supabase":
        auth_config = get_auth_config()
        if not auth_config.enabled:
            return SupabaseRepository(
                get_fixture_provider(),
                get_supabase_client(),
                get_market_data_runtime_service(),
            )
        return SupabaseRepository(
            get_fixture_provider(),
            get_supabase_client(),
            get_market_data_runtime_service(),
            organization_id=user.organization_id,
            actor_user_id=user.id,
        )
    return get_repository()


@lru_cache
def get_market_data_runtime_service() -> MarketDataRuntimeService:
    runtime_config = get_runtime_config()
    if runtime_config.repository_backend == "supabase":
        provider_runtime = build_supabase_provider_runtime(
            get_supabase_client(),
            request_budget=8,
        )
    else:
        provider_runtime = build_in_memory_provider_runtime(request_budget=8)
    return MarketDataRuntimeService(
        get_market_provider_config(),
        get_fixture_provider(),
        provider_runtime=provider_runtime,
    )


def get_provider_demo_service() -> ProviderDemoService:
    return ProviderDemoService(get_market_data_runtime_service())


@lru_cache
def get_llm_adapter() -> LLMAdapter:
    runtime_config = get_runtime_config()
    if runtime_config.llm_provider == "openai":
        return OpenAIResponsesAdapter()
    return FixtureLLMAdapter()


@lru_cache
def get_event_service(
    user: CurrentUserDep,
) -> EventService:
    return EventService(get_scoped_repository(user))


def get_differentiator_service(
    user: CurrentUserDep,
) -> DifferentiatorService:
    return DifferentiatorService(get_scoped_repository(user))


def get_conversation_service(
    user: CurrentUserDep,
) -> ConversationService:
    runtime_config = get_runtime_config()
    repository = (
        SupabaseConversationRepository(get_supabase_client())
        if runtime_config.repository_backend == "supabase"
        else get_in_memory_conversation_repository()
    )
    return ConversationService(repository, get_scoped_repository(user))


@lru_cache
def get_signal_service(
    user: CurrentUserDep,
) -> SignalService:
    return SignalService(get_scoped_repository(user))


@lru_cache
def get_market_service(
    user: CurrentUserDep,
) -> MarketService:
    return MarketService(get_scoped_repository(user))


@lru_cache
def get_review_service(
    user: CurrentUserDep,
) -> ReviewService:
    return ReviewService(get_scoped_repository(user))


@lru_cache
def get_briefing_service(
    user: CurrentUserDep,
) -> BriefingService:
    return BriefingService(get_scoped_repository(user), get_llm_adapter())


@lru_cache
def get_analysis_service(
    user: CurrentUserDep,
) -> AnalysisService:
    return AnalysisService(get_scoped_repository(user), get_llm_adapter())
