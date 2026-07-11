from __future__ import annotations

import pytest

from app.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_REASONING_EFFORT,
    REPO_ROOT,
    get_openai_config,
    get_runtime_config,
)


def test_openai_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_REASONING_EFFORT", raising=False)

    config = get_openai_config()

    assert config.api_key == "test-key"
    assert config.model == DEFAULT_OPENAI_MODEL
    assert config.reasoning_effort == DEFAULT_OPENAI_REASONING_EFFORT


def test_openai_config_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        get_openai_config()


def test_openai_config_rejects_invalid_reasoning_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "turbo")

    with pytest.raises(RuntimeError, match="OPENAI_REASONING_EFFORT must be one of"):
        get_openai_config()


def test_runtime_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FIXTURE_BUNDLE_PATH", raising=False)

    config = get_runtime_config()

    assert config.llm_provider == DEFAULT_LLM_PROVIDER
    assert config.fixture_bundle_path == (
        REPO_ROOT / "data/fixtures/v1/phase0_bundle.json"
    ).resolve()
