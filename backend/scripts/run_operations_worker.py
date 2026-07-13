#!/usr/bin/env python3
"""Run NexoMercado operational worker tasks and emit metrics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402

from app.api.dependencies import get_supabase_client  # noqa: E402
from app.config import get_market_provider_config, get_runtime_config  # noqa: E402
from app.operations.store import InMemoryOperationStore, SupabaseOperationStore  # noqa: E402
from app.operations.worker import run_operations_worker  # noqa: E402
from app.providers.fixture_provider import FixtureProvider  # noqa: E402
from app.providers.live_market import MarketDataRuntimeService  # noqa: E402
from app.services.provider_runtime_service import build_in_memory_provider_runtime  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task",
        choices=("ingest", "prices", "macro", "reconcile", "cleanup", "all"),
        default="all",
    )
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--format", choices=("json", "prometheus"), default="json")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)

    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    provider_config = get_market_provider_config()
    runtime = build_in_memory_provider_runtime(request_budget=provider_config.request_budget)
    trace.set_tracer_provider(TracerProvider())
    market_service = MarketDataRuntimeService(
        provider_config,
        fixture_provider,
        request_budget=provider_config.request_budget,
        provider_runtime=runtime,
    )
    runtime_config = get_runtime_config()
    store = (
        SupabaseOperationStore(get_supabase_client())
        if runtime_config.repository_backend == "supabase"
        else InMemoryOperationStore()
    )
    report = run_operations_worker(
        task=args.task,
        market_service=market_service,
        fixture_provider=fixture_provider,
        provider_runtime=runtime,
        store=store,
    )
    if args.format == "prometheus":
        print(report.to_prometheus())
    else:
        print(json.dumps(report.to_json(), ensure_ascii=False))
    if not report.ok:
        return 2
    return 1 if report.partial else 0


if __name__ == "__main__":
    raise SystemExit(main())
