"""Dependency providers for the NexoMercado HTTP API."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_market_provider_config, get_runtime_config, get_supabase_config
from app.llm.base import LLMAdapter
from app.llm.fixture_adapter import FixtureLLMAdapter
from app.llm.openai_responses import OpenAIResponsesAdapter
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService
from app.providers.provider_cache import InMemoryProviderCacheStore, SupabaseProviderCacheStore
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.supabase_repository import SupabaseRepository
from app.services.analysis_service import AnalysisService
from app.services.briefing_service import BriefingService
from app.services.event_service import EventService
from app.services.review_service import ReviewService
from app.services.signal_service import SignalService
from app.supabase_client import create_supabase_client


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
def get_market_data_runtime_service() -> MarketDataRuntimeService:
    runtime_config = get_runtime_config()
    provider_cache = InMemoryProviderCacheStore()
    if runtime_config.repository_backend == "supabase":
        provider_cache = SupabaseProviderCacheStore(get_supabase_client())
    return MarketDataRuntimeService(
        get_market_provider_config(),
        get_fixture_provider(),
        provider_cache=provider_cache,
    )


@lru_cache
def get_llm_adapter() -> LLMAdapter:
    runtime_config = get_runtime_config()
    if runtime_config.llm_provider == "openai":
        return OpenAIResponsesAdapter()
    return FixtureLLMAdapter()


@lru_cache
def get_event_service() -> EventService:
    return EventService(get_repository())


@lru_cache
def get_signal_service() -> SignalService:
    return SignalService(get_repository())


@lru_cache
def get_review_service() -> ReviewService:
    return ReviewService(get_repository())


@lru_cache
def get_briefing_service() -> BriefingService:
    return BriefingService(get_repository(), get_llm_adapter())


@lru_cache
def get_analysis_service() -> AnalysisService:
    return AnalysisService(get_repository(), get_llm_adapter())
