#!/usr/bin/env python3
"""Run a persistence smoke for reviews, briefings and runs against Supabase."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.contracts.api import AgentRunStep, AnalysisRequest, BriefingRequest, ReviewRequest  # noqa: E402
from app.contracts.entities import ReviewStatus  # noqa: E402
from app.providers.fixture_provider import FixtureProvider  # noqa: E402
from app.repositories.supabase_repository import SupabaseRepository  # noqa: E402
from app.supabase_client import create_supabase_client  # noqa: E402


def repository() -> SupabaseRepository:
    client = create_supabase_client()
    provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    return SupabaseRepository(provider, client)


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

    first = repository()
    signal_id = "sig_wti_context"

    if first.get_signal(signal_id).review.status != ReviewStatus.REVIEWED:
        review = ReviewRequest.model_validate(
            {
                "status": "reviewed",
                "justification": "Smoke de persistencia verificado.",
            }
        )
        first.create_signal_review(
            signal_id,
            review,
            idempotency_key="supabase-smoke-review-001",
        )

    briefing_request = BriefingRequest.model_validate(
        {
            "watchlistId": "watchlist_demo_global",
            "signalIds": [signal_id],
            "status": "shareable",
        }
    )
    briefing = first.create_briefing(
        briefing_request,
        idempotency_key="supabase-smoke-briefing-001",
        executive_summary="Smoke de briefing persistido.",
    )

    analysis_request = AnalysisRequest.model_validate(
        {
            "eventId": "evt_wti_inventory_20260708",
            "assetIds": ["ast_wti"],
        }
    )
    run, _ = first.create_analysis_run(
        analysis_request,
        idempotency_key="supabase-smoke-analysis-001",
        model_name="fixture-llm",
        prompt_version="supabase-smoke-v1",
    )
    step = AgentRunStep.model_validate(
        {
            "id": "step_supabase_smoke_001",
            "runId": run.id,
            "node": "load_context",
            "status": "processing",
            "timestamp": datetime(2026, 7, 12, 18, 0, tzinfo=UTC),
            "payload": {"eventId": analysis_request.event_id},
        }
    )
    first.append_run_step(run.id, step)
    first.complete_analysis_run(
        run.id,
        status="completed",
        current_node="pending_review",
    )

    restarted = repository()
    persisted_reviews = restarted.list_signal_reviews(signal_id)
    persisted_briefing = restarted.get_briefing(briefing.briefing_id)
    persisted_run = restarted.get_analysis_run(run.id)
    persisted_steps = restarted.get_run_steps(run.id)

    result = {
        "ok": bool(
            persisted_reviews
            and persisted_steps
            and persisted_briefing.status.value == "shareable"
            and persisted_run.status.value == "completed"
        ),
        "signalId": signal_id,
        "reviewStatus": restarted.get_signal(signal_id).review.status.value,
        "briefingId": persisted_briefing.briefing_id,
        "briefingStatus": persisted_briefing.status.value,
        "runId": persisted_run.id,
        "runStatus": persisted_run.status.value,
        "stepCount": len(persisted_steps),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
