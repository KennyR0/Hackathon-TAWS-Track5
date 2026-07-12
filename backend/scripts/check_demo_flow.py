#!/usr/bin/env python3
"""Smoke the local demo flow: radar -> signal -> evidence -> review -> briefing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app  # noqa: E402


def _expect_ok(response, *, expected_status: int = 200) -> dict[str, object]:
    if response.status_code != expected_status:
        raise RuntimeError(
            f"Expected HTTP {expected_status}, got {response.status_code}: {response.text}"
        )
    return response.json()


def main() -> int:
    with TestClient(create_app()) as client:
        events_payload = _expect_ok(client.get("/api/v1/events"))
        events = events_payload["data"]
        if not events:
            raise RuntimeError("Radar returned no events")
        event_id = events[0]["event"]["id"]

        signal_payload = _expect_ok(client.get("/api/v1/signals/sig_btc_uncertain"))
        evidence_payload = _expect_ok(client.get("/api/v1/signals/sig_btc_uncertain/evidence"))
        if not evidence_payload["data"]:
            raise RuntimeError("Signal evidence endpoint returned no evidence")
        similar_payload = _expect_ok(client.get(f"/api/v1/events/{event_id}/similar"))
        if not similar_payload["data"]:
            raise RuntimeError("Similar events endpoint returned no comparisons")
        ecuador_payload = _expect_ok(client.get("/api/v1/ecuador-snapshots"))
        if not ecuador_payload["data"]:
            raise RuntimeError("Ecuador snapshots endpoint returned no snapshots")
        conversation_payload = _expect_ok(
            client.post(
                "/api/v1/conversations",
                json={"watchlistId": "watchlist_demo_global"},
            ),
            expected_status=201,
        )
        conversation_id = conversation_payload["data"]["id"]
        message_payload = _expect_ok(
            client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json={"content": "Explica la senal con evidencia y contexto Ecuador."},
            ),
            expected_status=201,
        )

        review_payload = _expect_ok(
            client.post(
                "/api/v1/signals/sig_btc_uncertain/reviews",
                headers={"Idempotency-Key": "demo-flow-review-001"},
                json={
                    "status": "escalated",
                    "justification": "Smoke local: requiere revision humana antes de compartir.",
                },
            ),
            expected_status=201,
        )

        signals_payload = _expect_ok(client.get("/api/v1/signals"))
        signal_ids = [signal["id"] for signal in signals_payload["data"]]
        briefing_payload = _expect_ok(
            client.post(
                "/api/v1/briefings",
                headers={"Idempotency-Key": "demo-flow-briefing-001"},
                json={
                    "watchlistId": "watchlist_demo_global",
                    "signalIds": signal_ids,
                    "status": "draft",
                },
            ),
            expected_status=201,
        )

    result = {
        "ok": True,
        "flow": ["radar", "signal", "evidence", "review", "briefing"],
        "eventCount": len(events),
        "signalId": signal_payload["data"]["id"],
        "evidenceCount": len(evidence_payload["data"]),
        "similarEventCount": len(similar_payload["data"]),
        "ecuadorSnapshotCount": len(ecuador_payload["data"]),
        "conversationId": conversation_id,
        "conversationMessageId": message_payload["data"]["id"],
        "reviewStatus": review_payload["data"][-1]["status"],
        "briefingId": briefing_payload["data"]["briefingId"],
        "briefingStatus": briefing_payload["data"]["status"],
        "dataMode": briefing_payload.get("meta", {}).get("dataMode"),
        "warnings": briefing_payload.get("meta", {}).get("warnings", []),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
