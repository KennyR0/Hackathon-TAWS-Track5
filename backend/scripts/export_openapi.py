#!/usr/bin/env python3
"""Export or verify the deterministic OpenAPI contract snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
OPENAPI_PATH = REPO_ROOT / "contracts" / "openapi.json"
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts import build_openapi_document  # noqa: E402


def rendered_openapi() -> bytes:
    document = build_openapi_document()
    rendered = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return rendered.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail instead of writing when the committed snapshot differs.",
    )
    args = parser.parse_args()
    expected = rendered_openapi()
    if args.check:
        if not OPENAPI_PATH.is_file() or OPENAPI_PATH.read_bytes() != expected:
            print(f"OpenAPI snapshot is stale: {OPENAPI_PATH}", file=sys.stderr)
            return 1
        print(f"OpenAPI snapshot is current: {OPENAPI_PATH}")
        return 0
    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_bytes(expected)
    print(f"Wrote {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

