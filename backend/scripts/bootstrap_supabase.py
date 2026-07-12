#!/usr/bin/env python3
"""Idempotently load the mutable demo graph into Supabase."""

from __future__ import annotations

import argparse
import sys
from hashlib import sha256
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.providers.fixture_provider import FixtureProvider  # noqa: E402
from app.repositories.fixture_repository import FixtureRepository  # noqa: E402
from app.supabase_client import create_supabase_client  # noqa: E402


def _existing_ids(client, table: str) -> set[str]:
    rows = client.table(table).select("id").execute().data or []
    return {row["id"] for row in rows if "id" in row}


def _existing_pairs(client, table: str, left: str, right: str) -> set[tuple[str, str]]:
    rows = client.table(table).select(f"{left},{right}").execute().data or []
    return {
        (row[left], row[right])
        for row in rows
        if left in row and right in row
    }


def _upsert(client, table: str, rows: list[dict], *, conflict: str | None = None) -> None:
    if not rows:
        return
    query = client.table(table).upsert(rows, on_conflict=conflict)
    query.execute()


def bootstrap() -> dict[str, int]:
    client = create_supabase_client()
    repository = FixtureRepository(
        FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    )
    bundle = repository._bundle

    _upsert(
        client,
        "organizations",
        [{"id": "org_demo", "name": "NexoMercado Demo"}],
    )
    existing_review_ids = _existing_ids(client, "signal_reviews")
    _upsert(
        client,
        "signal_reviews",
        [
            {
                "id": review.id,
                "signal_id": review.signal_id,
                "previous_status": review.previous_status.value,
                "status": review.status.value,
                "justification": review.justification,
                "reviewed_by": review.reviewed_by.id,
                "reviewed_at": review.reviewed_at.isoformat(),
                "created_at": review.created_at.isoformat(),
            }
            for review in bundle.signal_reviews
            if review.id not in existing_review_ids
        ],
    )

    for briefing in bundle.briefings:
        summary = briefing.human_review_summary
        _upsert(
            client,
            "briefings",
            [
                {
                    "id": briefing.briefing_id,
                    "organization_id": "org_demo",
                    "watchlist_id": briefing.watchlist.id,
                    "status": briefing.status.value,
                    "executive_summary": briefing.executive_summary,
                    "total_signals": summary.total_signals,
                    "pending_review_count": summary.pending_review,
                    "reviewed_count": summary.reviewed,
                    "escalated_count": summary.escalated,
                    "discarded_count": summary.discarded,
                    "requires_human_review": briefing.requires_human_review,
                    "disclaimer": briefing.disclaimer,
                    "created_at": briefing.created_at.isoformat(),
                    "updated_at": briefing.updated_at.isoformat(),
                }
            ],
        )
        _upsert(
            client,
            "briefing_signals",
            [
                {
                    "briefing_id": briefing.briefing_id,
                    "signal_id": item.signal_id,
                    "priority": item.priority,
                    "reason": item.reason,
                    "suggested_research_actions": list(item.suggested_research_actions),
                    "position": index,
                }
                for index, item in enumerate(briefing.prioritized_signals)
            ],
            conflict="briefing_id,signal_id",
        )
        _upsert(
            client,
            "idempotency_keys",
            [
                {
                    "organization_id": "org_demo",
                    "operation": "briefing",
                    "idempotency_key": f"bootstrap-{briefing.briefing_id}",
                    "request_hash": (
                        "sha256:"
                        + sha256(briefing.briefing_id.encode("utf-8")).hexdigest()
                    ),
                    "response_status": 200,
                    "response_body": briefing.model_dump(mode="json", by_alias=True),
                    "expires_at": repository.fixture_clock.isoformat(),
                }
            ],
            conflict="organization_id,operation,idempotency_key",
        )

    _upsert(
        client,
        "agent_runs",
        [
            {
                "id": run.id,
                "organization_id": run.organization_id,
                "conversation_id": run.conversation_id,
                "current_node": run.current_node,
                "status": run.status.value,
                "model_name": run.model_name,
                "prompt_version": run.prompt_version,
                "input_hash": run.input_hash,
                "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "error_code": run.error_code,
                "retry_count": run.retry_count,
            }
            for run in bundle.agent_runs
        ],
    )
    existing_snapshot_links = _existing_pairs(
        client,
        "agent_run_source_snapshots",
        "run_id",
        "snapshot_id",
    )
    snapshot_rows = [
        {
            "run_id": run.id,
            "snapshot_id": snapshot_id,
            "snapshot_kind": (
                "market" if snapshot_id.startswith("mkt_") else "raw_source"
            ),
        }
        for run in bundle.agent_runs
        for snapshot_id in run.source_snapshot_ids
        if (run.id, snapshot_id) not in existing_snapshot_links
    ]
    if snapshot_rows:
        client.table("agent_run_source_snapshots").insert(snapshot_rows).execute()

    return {
        "reviews": len(bundle.signal_reviews),
        "briefings": len(bundle.briefings),
        "runs": len(bundle.agent_runs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional dotenv file with Supabase credentials",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the mutable demo graph to Supabase",
    )
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    if not args.apply:
        print("Use --apply to write the mutable demo graph.")
        return 0

    print(bootstrap())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
