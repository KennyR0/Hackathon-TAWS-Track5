#!/usr/bin/env python3
"""Check the current backend runtime posture for fixture, Supabase and market-data mode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_market_provider_config, get_runtime_config  # noqa: E402
from app.providers.fixture_provider import FixtureProvider  # noqa: E402
from app.providers.live_market import MarketDataRuntimeService  # noqa: E402
from app.supabase_client import create_supabase_client, verify_supabase_connection  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Optional dotenv file with runtime configuration")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)

    runtime_config = get_runtime_config()
    market_service = MarketDataRuntimeService(
        get_market_provider_config(),
        FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json"),
    )
    market_snapshot = market_service.collect_demo_snapshot()

    supabase_result: dict[str, object] = {"enabled": runtime_config.repository_backend == "supabase"}
    if runtime_config.repository_backend == "supabase":
        connection = verify_supabase_connection(create_supabase_client())
        supabase_result.update(
            {
                "ok": connection.is_connected,
                "resource": connection.resource,
                "rowsRead": connection.rows_read,
            }
        )

    print(
        json.dumps(
            {
                "repositoryBackend": runtime_config.repository_backend,
                "llmProvider": runtime_config.llm_provider,
                "marketDataMode": runtime_config.market_data_mode,
                "supabase": supabase_result,
                "marketData": {
                    "effectiveDataMode": market_snapshot.data_mode,
                    "provider": market_snapshot.provider,
                    "warnings": list(market_snapshot.warnings),
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
