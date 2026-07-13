#!/usr/bin/env python3
"""Validate the 25-instrument market universe without exposing credentials."""

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
from app.market_universe import load_market_universe  # noqa: E402
from app.providers.fixture_provider import FixtureProvider  # noqa: E402
from app.providers.live_market import MarketDataRuntimeService  # noqa: E402
from app.services.provider_runtime_service import build_in_memory_provider_runtime  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)

    config = get_market_provider_config()
    universe = load_market_universe()
    runtime = build_in_memory_provider_runtime(request_budget=config.request_budget)
    service = MarketDataRuntimeService(
        config,
        FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json"),
        request_budget=config.request_budget,
        provider_runtime=runtime,
    )
    results = {}
    for offset in range(0, len(universe.instruments), 10):
        batch = universe.instruments[offset : offset + 10]
        results.update(service.collect_quotes(batch))

    live = sorted(symbol for symbol, result in results.items() if result.ok)
    fallback = sorted(symbol for symbol, result in results.items() if not result.ok)
    payload = {
        "ok": len(results) == 25,
        "configuredMode": config.mode,
        "universeVersion": universe.version,
        "instrumentCount": len(universe.instruments),
        "resultCount": len(results),
        "liveCount": len(live),
        "fallbackCount": len(fallback),
        "liveSymbols": live,
        "fallbackSymbols": fallback,
        "providers": sorted({result.provider for result in results.values()}),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
