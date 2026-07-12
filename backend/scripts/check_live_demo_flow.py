#!/usr/bin/env python3
"""Run the real HTTP demo against an already running NexoMercado backend."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from time import monotonic, sleep
from uuid import uuid4

import httpx


def _expect_json(response: httpx.Response, *expected_statuses: int) -> dict[str, object]:
    if response.status_code not in expected_statuses:
        raise RuntimeError(
            f"{response.request.method} {response.request.url} returned "
            f"HTTP {response.status_code}: {response.text}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object from {response.request.url}")
    return payload


def _wait_for_analysis(
    client: httpx.Client,
    run_id: str,
    *,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        payload = _expect_json(client.get(f"/api/v1/analyses/{run_id}"), 200)
        run = payload["data"]
        if not isinstance(run, dict):
            raise RuntimeError("Analysis response did not include a run object")
        if run.get("status") != "processing":
            return run
        sleep(1)
    raise RuntimeError(f"Analysis {run_id} did not finish within {timeout_seconds:.0f}s")


def _next_review_status(current: str) -> str:
    return "reviewed" if current == "escalated" else "escalated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--analysis-timeout", type=float, default=120.0)
    args = parser.parse_args()

    session_id = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    marker = f"DEMO_E2E:{session_id}"
    headers = {"Accept": "application/json"}
    access_token = os.getenv("DEMO_ACCESS_TOKEN", "").strip()
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    with httpx.Client(
        base_url=args.base_url.rstrip("/"),
        headers=headers,
        timeout=45.0,
    ) as client:
        health = _expect_json(client.get("/health"), 200)
        provider_payload = _expect_json(client.get("/api/v1/runtime/providers"), 200)
        provider_status = provider_payload["data"]
        provider_checks = provider_status["checks"]
        live_checks = [
            check
            for check in provider_checks
            if check.get("ok") is True and check.get("dataMode") == "live"
        ]
        if not live_checks:
            raise RuntimeError("No external provider returned a live result")

        events_payload = _expect_json(client.get("/api/v1/events"), 200)
        events = events_payload["data"]
        event_view = next(
            item for item in events if item.get("event", {}).get("relatedAssets")
        )
        event = event_view["event"]
        asset_ids = [item["assetId"] for item in event["relatedAssets"]]

        signals_payload = _expect_json(client.get("/api/v1/signals"), 200)
        signals = signals_payload["data"]
        if not signals:
            raise RuntimeError("The radar returned no signals")
        signal = signals[0]
        signal_id = signal["id"]
        evidence_payload = _expect_json(
            client.get(f"/api/v1/signals/{signal_id}/evidence"),
            200,
        )
        if not evidence_payload["data"]:
            raise RuntimeError(f"Signal {signal_id} has no evidence")

        conversation_payload = _expect_json(
            client.post(
                "/api/v1/conversations",
                json={"watchlistId": "watchlist_demo_global"},
            ),
            201,
        )
        conversation_id = conversation_payload["data"]["id"]
        _expect_json(
            client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={
                    "content": (
                        f"{marker} Explica la senal con evidencia y contexto Ecuador."
                    )
                },
            ),
            201,
        )
        loaded_conversation = _expect_json(
            client.get(f"/api/v1/conversations/{conversation_id}"),
            200,
        )
        messages = loaded_conversation["data"]["messages"]
        if not any(marker in message.get("content", "") for message in messages):
            raise RuntimeError("The persisted conversation did not retain the demo marker")

        analysis_payload = _expect_json(
            client.post(
                "/api/v1/analyses",
                headers={"Idempotency-Key": f"demo-analysis-{session_id}"},
                json={"eventId": event["id"], "assetIds": asset_ids},
            ),
            202,
        )
        run_id = analysis_payload["data"]["id"]
        run = _wait_for_analysis(
            client,
            run_id,
            timeout_seconds=args.analysis_timeout,
        )
        if run.get("status") == "failed":
            raise RuntimeError(f"OpenAI analysis failed: {run.get('errorCode')}")
        if run.get("modelName") in {None, "fixture-llm"}:
            raise RuntimeError("Analysis did not report a real OpenAI model")

        steps_payload = _expect_json(client.get(f"/api/v1/runs/{run_id}/steps"), 200)
        step_nodes = {step["node"] for step in steps_payload["data"]}
        required_nodes = {"analyst_agent", "advisor_agent", "audit_writer"}
        missing_nodes = sorted(required_nodes - step_nodes)
        if missing_nodes:
            raise RuntimeError(f"Analysis is missing required nodes: {missing_nodes}")

        current_review_status = signal.get("review", {}).get("status", "pending_review")
        review_status = _next_review_status(current_review_status)
        review_payload = _expect_json(
            client.post(
                f"/api/v1/signals/{signal_id}/reviews",
                headers={"Idempotency-Key": f"demo-review-{session_id}"},
                json={
                    "status": review_status,
                    "justification": f"{marker} Revision humana del demostrativo real.",
                },
            ),
            201,
        )

        briefing_payload = _expect_json(
            client.post(
                "/api/v1/briefings",
                headers={"Idempotency-Key": f"demo-briefing-{session_id}"},
                json={
                    "watchlistId": "watchlist_demo_global",
                    "signalIds": [item["id"] for item in signals],
                    "status": "draft",
                },
            ),
            201,
        )
        briefing_id = briefing_payload["data"]["briefingId"]
        loaded_briefing = _expect_json(
            client.get(f"/api/v1/briefings/{briefing_id}"),
            200,
        )

    result = {
        "ok": True,
        "marker": marker,
        "health": health["status"],
        "providerMode": provider_status["effectiveDataMode"],
        "liveProviders": [item["provider"] for item in live_checks],
        "fallbackProviders": [
            item["provider"] for item in provider_checks if item["dataMode"] == "fallback"
        ],
        "eventId": event["id"],
        "signalId": signal_id,
        "evidenceCount": len(evidence_payload["data"]),
        "conversationId": conversation_id,
        "runId": run_id,
        "runStatus": run["status"],
        "modelName": run["modelName"],
        "verifiedNodes": sorted(required_nodes),
        "reviewStatus": review_payload["data"][-1]["status"],
        "briefingId": loaded_briefing["data"]["briefingId"],
        "briefingStatus": loaded_briefing["data"]["status"],
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
