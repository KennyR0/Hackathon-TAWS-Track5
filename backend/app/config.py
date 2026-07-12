"""Runtime configuration helpers for the NexoMercado backend."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = APP_ROOT.parent
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_OPENAI_MODEL = "gpt-5.4"
DEFAULT_OPENAI_REASONING_EFFORT = "medium"
DEFAULT_LLM_PROVIDER = "fixture"
DEFAULT_REPOSITORY_BACKEND = "fixture"
DEFAULT_FIXTURE_BUNDLE_PATH = "data/fixtures/v1/phase0_bundle.json"
VALID_REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}
VALID_LLM_PROVIDERS = {"fixture", "openai"}
VALID_REPOSITORY_BACKENDS = {"fixture", "supabase"}


@dataclass(frozen=True)
class RuntimeConfig:
    llm_provider: str = DEFAULT_LLM_PROVIDER
    repository_backend: str = DEFAULT_REPOSITORY_BACKEND
    fixture_bundle_path: Path = Path(DEFAULT_FIXTURE_BUNDLE_PATH)


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = DEFAULT_OPENAI_MODEL
    reasoning_effort: str = DEFAULT_OPENAI_REASONING_EFFORT


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    service_role_key: str


def get_openai_config() -> OpenAIConfig:
    """Load the OpenAI runtime config from environment variables."""

    api_key = getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to use OpenAI-backed agents")

    model = getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    reasoning_effort = (
        getenv("OPENAI_REASONING_EFFORT", DEFAULT_OPENAI_REASONING_EFFORT).strip().lower()
        or DEFAULT_OPENAI_REASONING_EFFORT
    )
    if reasoning_effort not in VALID_REASONING_EFFORTS:
        valid_values = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise RuntimeError(
            "OPENAI_REASONING_EFFORT must be one of: "
            f"{valid_values}. Received: {reasoning_effort}"
        )

    return OpenAIConfig(
        api_key=api_key,
        model=model,
        reasoning_effort=reasoning_effort,
    )


def get_runtime_config() -> RuntimeConfig:
    """Load non-secret runtime config for the backend."""

    llm_provider = getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER).strip().lower()
    if llm_provider not in VALID_LLM_PROVIDERS:
        valid_values = ", ".join(sorted(VALID_LLM_PROVIDERS))
        raise RuntimeError(
            "LLM_PROVIDER must be one of: "
            f"{valid_values}. Received: {llm_provider}"
        )

    repository_backend = getenv(
        "REPOSITORY_BACKEND",
        DEFAULT_REPOSITORY_BACKEND,
    ).strip().lower()
    if repository_backend not in VALID_REPOSITORY_BACKENDS:
        valid_values = ", ".join(sorted(VALID_REPOSITORY_BACKENDS))
        raise RuntimeError(
            "REPOSITORY_BACKEND must be one of: "
            f"{valid_values}. Received: {repository_backend}"
        )

    fixture_bundle_path = Path(
        getenv("FIXTURE_BUNDLE_PATH", DEFAULT_FIXTURE_BUNDLE_PATH).strip()
        or DEFAULT_FIXTURE_BUNDLE_PATH
    )
    if not fixture_bundle_path.is_absolute():
        fixture_bundle_path = REPO_ROOT / fixture_bundle_path

    return RuntimeConfig(
        llm_provider=llm_provider,
        repository_backend=repository_backend,
        fixture_bundle_path=fixture_bundle_path.resolve(),
    )


def get_supabase_config() -> SupabaseConfig:
    """Load privileged server-side Supabase credentials from environment variables."""

    url = getenv("SUPABASE_URL", "").strip()
    service_role_key = getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not service_role_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
            "to use the Supabase-backed repository"
        )
    if not url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL must use https")

    return SupabaseConfig(
        url=url,
        service_role_key=service_role_key,
    )
