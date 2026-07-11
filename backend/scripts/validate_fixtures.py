#!/usr/bin/env python3
"""Validate the complete Phase 0 fixture graph without network access."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEFAULT_BUNDLE = REPO_ROOT / "data" / "fixtures" / "v1" / "phase0_bundle.json"
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts import load_fixture_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args()
    bundle = load_fixture_bundle(args.path)
    print(
        "Validated fixture bundle "
        f"{bundle.manifest.fixture_id}: "
        f"{len(bundle.events)} events, "
        f"{len(bundle.signals)} signals, "
        f"{len(bundle.evidence)} evidence records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

