from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.main import create_app
from app.contracts.api import build_openapi_document

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
OPENAPI_SNAPSHOT = REPO_ROOT / "contracts" / "openapi.json"
CONSUMER_FIELDS = REPO_ROOT / "contracts" / "consumer-fields.json"


@pytest.fixture(scope="session")
def openapi_document() -> dict[str, object]:
    return build_openapi_document()


@pytest.fixture(scope="session")
def consumer_manifest() -> dict[str, object]:
    return json.loads(CONSUMER_FIELDS.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def reset_backend_singletons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "fixture")
    monkeypatch.setenv("REPOSITORY_BACKEND", "fixture")
    monkeypatch.setenv("MARKET_DATA_MODE", "fixture")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("GDELT_API_KEY", raising=False)
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)
    dependencies.get_fixture_provider.cache_clear()
    dependencies.get_market_data_runtime_service.cache_clear()
    dependencies.get_supabase_client.cache_clear()
    dependencies.get_repository.cache_clear()
    dependencies.get_llm_adapter.cache_clear()
    dependencies.get_event_service.cache_clear()
    dependencies.get_signal_service.cache_clear()
    dependencies.get_review_service.cache_clear()
    dependencies.get_briefing_service.cache_clear()
    dependencies.get_analysis_service.cache_clear()


@pytest.fixture
def api_client() -> TestClient:
    with TestClient(create_app()) as client:
        yield client
