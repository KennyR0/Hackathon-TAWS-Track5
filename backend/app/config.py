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
DEFAULT_MARKET_DATA_MODE = "fixture"
DEFAULT_FIXTURE_BUNDLE_PATH = "data/fixtures/v1/phase0_bundle.json"
DEFAULT_BACKEND_CORS_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "https://hackathon-taws-track5.vercel.app",
)
VALID_REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}
VALID_LLM_PROVIDERS = {"fixture", "openai"}
VALID_REPOSITORY_BACKENDS = {"fixture", "supabase"}
VALID_MARKET_DATA_MODES = {"fixture", "hybrid", "live"}


@dataclass(frozen=True)
class RuntimeConfig:
    llm_provider: str = DEFAULT_LLM_PROVIDER
    repository_backend: str = DEFAULT_REPOSITORY_BACKEND
    market_data_mode: str = DEFAULT_MARKET_DATA_MODE
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


@dataclass(frozen=True)
class MarketProviderConfig:
    mode: str = DEFAULT_MARKET_DATA_MODE
    gdelt_api_key: str | None = None
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    gdelt_user_agent: str = "NexoMercadoAI/1.0"
    gdelt_timeout_seconds: float = 6.0
    gdelt_max_attempts: int = 2
    gdelt_cache_ttl_seconds: int = 900
    finnhub_api_key: str | None = None
    twelve_data_api_key: str | None = None
    coingecko_api_key: str | None = None
    fred_api_key: str | None = None
    request_budget: int = 32
    batch_size: int = 10
    refresh_seconds: int = 900


def _parse_csv_env(value: str) -> tuple[str, ...]:
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


def _get_env_int(name: str, default: int) -> int:
    raw = getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer. Received: {raw}") from exc
    if value < 1:
        raise RuntimeError(f"{name} must be >= 1. Received: {value}")
    return value


def _get_env_float(name: str, default: float) -> float:
    raw = getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number. Received: {raw}") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be > 0. Received: {value}")
    return value


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
            f"OPENAI_REASONING_EFFORT must be one of: {valid_values}. Received: {reasoning_effort}"
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
        raise RuntimeError(f"LLM_PROVIDER must be one of: {valid_values}. Received: {llm_provider}")

    repository_backend = (
        getenv(
            "REPOSITORY_BACKEND",
            DEFAULT_REPOSITORY_BACKEND,
        )
        .strip()
        .lower()
    )
    if repository_backend not in VALID_REPOSITORY_BACKENDS:
        valid_values = ", ".join(sorted(VALID_REPOSITORY_BACKENDS))
        raise RuntimeError(
            f"REPOSITORY_BACKEND must be one of: {valid_values}. Received: {repository_backend}"
        )

    market_data_mode = (
        getenv(
            "MARKET_DATA_MODE",
            DEFAULT_MARKET_DATA_MODE,
        )
        .strip()
        .lower()
    )
    if market_data_mode not in VALID_MARKET_DATA_MODES:
        valid_values = ", ".join(sorted(VALID_MARKET_DATA_MODES))
        raise RuntimeError(
            f"MARKET_DATA_MODE must be one of: {valid_values}. Received: {market_data_mode}"
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
        market_data_mode=market_data_mode,
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


def get_backend_cors_origins() -> tuple[str, ...]:
    """Load explicit browser origins allowed to call the backend."""

    raw_origins = getenv("BACKEND_CORS_ORIGINS", "").strip()
    if not raw_origins:
        return DEFAULT_BACKEND_CORS_ORIGINS
    origins = _parse_csv_env(raw_origins)
    if "*" in origins:
        raise RuntimeError(
            "BACKEND_CORS_ORIGINS must list explicit origins; wildcard is not allowed"
        )
    return tuple(dict.fromkeys((*DEFAULT_BACKEND_CORS_ORIGINS, *origins)))


def get_market_provider_config() -> MarketProviderConfig:
    runtime_config = get_runtime_config()
    return MarketProviderConfig(
        mode=runtime_config.market_data_mode,
        gdelt_api_key=getenv("GDELT_API_KEY", "").strip() or None,
        gdelt_base_url=(
            getenv("GDELT_BASE_URL", "").strip() or "https://api.gdeltproject.org/api/v2/doc/doc"
        ),
        gdelt_user_agent=(getenv("SEC_USER_AGENT", "").strip() or "NexoMercadoAI/1.0"),
        gdelt_timeout_seconds=_get_env_float("GDELT_TIMEOUT_SECONDS", 6.0),
        gdelt_max_attempts=_get_env_int("GDELT_MAX_ATTEMPTS", 2),
        gdelt_cache_ttl_seconds=_get_env_int("GDELT_CACHE_TTL_SECONDS", 900),
        finnhub_api_key=getenv("FINNHUB_API_KEY", "").strip() or None,
        twelve_data_api_key=getenv("TWELVE_DATA_API_KEY", "").strip() or None,
        coingecko_api_key=getenv("COINGECKO_API_KEY", "").strip() or None,
        fred_api_key=getenv("FRED_API_KEY", "").strip() or None,
        request_budget=_get_env_int("MARKET_REQUEST_BUDGET", 32),
        batch_size=_get_env_int("MARKET_BATCH_SIZE", 10),
        refresh_seconds=_get_env_int("MARKET_REFRESH_SECONDS", 900),
    )
