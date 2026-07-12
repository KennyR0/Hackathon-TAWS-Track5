#!/usr/bin/env python3
"""Probe the market-data runtime in fixture, hybrid or live mode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_market_provider_config  # noqa: E402
from app.providers.fixture_provider import FixtureProvider  # noqa: E402
from app.providers.live_market import MarketDataRuntimeService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Optional dotenv file with provider credentials")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)

    service = MarketDataRuntimeService(
        get_market_provider_config(),
        FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json"),
    )
    snapshot = service.collect_demo_snapshot()
    print(
        json.dumps(
            {
                "mode": service.mode,
                "effectiveDataMode": snapshot.data_mode,
                "provider": snapshot.provider,
                "warnings": list(snapshot.warnings),
                "requestBudget": snapshot.request_budget,
                "requestsUsed": snapshot.requests_used,
                "checks": {
                    key: {
                        "provider": value.provider,
                        "dataMode": value.data_mode,
                        "ok": value.ok,
                        "warnings": list(value.warnings),
                        "payload": value.payload,
                    }
                    for key, value in snapshot.checks.items()
                },
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
