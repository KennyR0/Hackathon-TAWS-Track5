#!/usr/bin/env python3
"""Validate the public Vercel + Render deployment without requiring secrets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from time import monotonic, sleep
from uuid import uuid4

import httpx

DEFAULT_FRONTEND_URL = "https://hackathon-taws-track5.vercel.app/summary"
DEFAULT_BACKEND_URL = "https://hackathon-taws-track5.onrender.com"
FRONTEND_READY_MARKERS = ("AAPL", "Señales priorizadas", "Radar")


def _expect_json(response: httpx.Response, *expected_statuses: int) -> dict[str, object]:
    if response.status_code not in expected_statuses:
        raise RuntimeError(
            f"{response.request.method} {response.request.url} returned "
            f"HTTP {response.status_code}: {response.text[:500]}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object from {response.request.url}")
    return payload


def _check_frontend_html(client: httpx.Client, frontend_url: str) -> dict[str, object]:
    response = client.get(frontend_url)
    if response.status_code != 200:
        raise RuntimeError(f"Frontend returned HTTP {response.status_code}")
    html = response.text
    return {
        "ok": True,
        "title": "NexoMercado Finance" in html,
        "root": 'id="root"' in html,
        "assetBundle": "/assets/" in html,
    }


def _check_frontend_browser(frontend_url: str) -> dict[str, object]:
    chrome = (
        shutil.which("google-chrome")
        or shutil.which("chromium")
        or shutil.which("chromium-browser")
    )
    if chrome is None:
        return {"ok": None, "skipped": "chrome_not_available"}
    completed = subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=10000",
            "--dump-dom",
            frontend_url,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Browser check failed: {completed.stderr[:500]}")
    dom = completed.stdout
    missing = [marker for marker in FRONTEND_READY_MARKERS if marker not in dom]
    if missing:
        raise RuntimeError(f"Frontend did not render expected data markers: {missing}")
    return {"ok": True, "markers": list(FRONTEND_READY_MARKERS)}


def _check_cors(client: httpx.Client, backend_url: str, origin: str) -> dict[str, object]:
    response = client.options(
        f"{backend_url}/api/v1/events",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Idempotency-Key,Last-Event-ID",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"CORS preflight returned HTTP {response.status_code}")
    allowed_origin = response.headers.get("access-control-allow-origin")
    if allowed_origin != origin:
        raise RuntimeError(f"CORS origin mismatch: expected {origin}, got {allowed_origin}")
    return {"ok": True, "allowOrigin": allowed_origin}


def _wait_for_run(
    client: httpx.Client,
    run_id: str,
    *,
    timeout_seconds: float,
) -> dict[str, object]:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        payload = _expect_json(client.get(f"/api/v1/analyses/{run_id}"), 200)
        run = payload["data"]
        if isinstance(run, dict) and run.get("status") != "processing":
            return run
        sleep(1)
    raise RuntimeError(f"Run {run_id} did not finish within {timeout_seconds:.0f}s")


def _run_write_flow(
    client: httpx.Client,
    *,
    signals: list[dict[str, object]],
    events: list[dict[str, object]],
    timeout_seconds: float,
) -> dict[str, object]:
    session_id = f"PUBLIC_SMOKE:{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
    signal = signals[0]
    signal_id = str(signal["id"])
    current_review = signal.get("review")
    current_status = (
        current_review.get("status")
        if isinstance(current_review, dict) and isinstance(current_review.get("status"), str)
        else "pending_review"
    )
    next_status = "reviewed" if current_status == "escalated" else "escalated"
    review_justification = (
        "Revision publica controlada: la evidencia trazable y las advertencias "
        "del sistema permanecen visibles para la demostracion."
    )
    review = _expect_json(
        client.post(
            f"/api/v1/signals/{signal_id}/reviews",
            headers={"Idempotency-Key": f"public-smoke-review-{session_id}"},
            json={
                "status": next_status,
                "justification": review_justification,
            },
        ),
        201,
    )
    briefing = _expect_json(
        client.post(
            "/api/v1/briefings",
            headers={"Idempotency-Key": f"public-smoke-briefing-{session_id}"},
            json={
                "watchlistId": "watchlist_demo_global",
                "signalIds": [str(item["id"]) for item in signals],
                "status": "draft",
            },
        ),
        201,
    )
    event_view = next(
        item
        for item in events
        if isinstance(item.get("event"), dict) and item["event"].get("relatedAssets")
    )
    event = event_view["event"]
    analysis = _expect_json(
        client.post(
            "/api/v1/analyses",
            headers={"Idempotency-Key": f"public-smoke-analysis-{session_id}"},
            json={
                "eventId": event["id"],
                "assetIds": [item["assetId"] for item in event["relatedAssets"]],
            },
        ),
        202,
    )
    run_id = analysis["data"]["id"]
    run = _wait_for_run(client, str(run_id), timeout_seconds=timeout_seconds)
    steps = _expect_json(client.get(f"/api/v1/runs/{run_id}/steps"), 200)
    return {
        "marker": session_id,
        "reviewStatus": review["data"][-1]["status"],
        "briefingId": briefing["data"]["briefingId"],
        "runId": run_id,
        "runStatus": run["status"],
        "stepCount": len(steps["data"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--include-write-flow", action="store_true")
    parser.add_argument("--write-timeout", type=float, default=120.0)
    parser.add_argument("--skip-browser", action="store_true")
    parser.add_argument("--skip-cors", action="store_true")
    args = parser.parse_args()

    backend_url = args.backend_url.rstrip("/")
    frontend_origin = args.frontend_url.split("/summary", 1)[0].rstrip("/")
    result: dict[str, object] = {
        "frontendUrl": args.frontend_url,
        "backendUrl": backend_url,
        "writeFlow": "enabled" if args.include_write_flow else "disabled",
    }
    with httpx.Client(timeout=45.0) as public_client:
        result["frontendHtml"] = _check_frontend_html(public_client, args.frontend_url)
        if not args.skip_browser:
            result["frontendBrowser"] = _check_frontend_browser(args.frontend_url)
        if args.skip_cors:
            result["cors"] = {"ok": None, "skipped": "skip_cors_enabled"}
        else:
            result["cors"] = _check_cors(public_client, backend_url, frontend_origin)

    with httpx.Client(
        base_url=backend_url,
        timeout=45.0,
        headers={"Accept": "application/json"},
    ) as api:
        result["health"] = _expect_json(api.get("/health"), 200)
        events_payload = _expect_json(api.get("/api/v1/events"), 200)
        signals_payload = _expect_json(api.get("/api/v1/signals"), 200)
        runtime_payload = _expect_json(api.get("/api/v1/runtime/providers"), 200)
        events = events_payload["data"]
        signals = signals_payload["data"]
        if not isinstance(events, list) or not events:
            raise RuntimeError("Public events endpoint returned no rows")
        if not isinstance(signals, list) or not signals:
            raise RuntimeError("Public signals endpoint returned no rows")
        first_signal_id = str(signals[0]["id"])
        evidence_payload = _expect_json(api.get(f"/api/v1/signals/{first_signal_id}/evidence"), 200)
        if not evidence_payload["data"]:
            raise RuntimeError(f"Signal {first_signal_id} returned no evidence")
        result["events"] = {"count": len(events), "dataMode": events_payload["meta"]["dataMode"]}
        result["signals"] = {"count": len(signals), "firstSignalId": first_signal_id}
        result["evidence"] = {"count": len(evidence_payload["data"])}
        result["runtimeProviders"] = {
            "effectiveDataMode": runtime_payload["data"]["effectiveDataMode"],
            "warnings": runtime_payload["data"]["warnings"],
            "checks": len(runtime_payload["data"]["checks"]),
        }
        if args.include_write_flow:
            result["writeResult"] = _run_write_flow(
                api,
                signals=signals,
                events=events,
                timeout_seconds=args.write_timeout,
            )

    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
