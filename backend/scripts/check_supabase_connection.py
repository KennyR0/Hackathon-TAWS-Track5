#!/usr/bin/env python3
"""Verify backend connectivity to Supabase without printing secrets or row data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.supabase_client import create_supabase_client, verify_supabase_connection  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional dotenv file with Supabase credentials",
    )
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)

    result = verify_supabase_connection(create_supabase_client())
    print(
        json.dumps(
            {
                "ok": result.is_connected,
                "resource": result.resource,
                "rowsRead": result.rows_read,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
