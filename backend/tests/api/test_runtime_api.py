from __future__ import annotations

from time import sleep

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_app_user
from app.main import create_app
from app.security.auth import AppUserContext


def _wait_for_terminal_run(api_client, run_id: str) -> dict[str, object]:
    for _ in range(200):
        response = api_client.get(f"/api/v1/analyses/{run_id}")
        assert response.status_code == 200
        payload = response.json()["data"]
        if payload["status"] != "processing":
            return payload
        sleep(0.01)
    raise AssertionError(f"Run {run_id} did not reach a terminal state")


def test_health_endpoint(api_client) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "nexomercado-api",
        "contractVersion": "0.1.0",
    }


def test_cors_allows_configured_vercel_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "BACKEND_CORS_ORIGINS",
        "https://nexomercado-demo.vercel.app,http://localhost:5173",
    )

    with TestClient(create_app()) as client:
        response = client.options(
            "/api/v1/events",
            headers={
                "Origin": "https://nexomercado-demo.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://nexomercado-demo.vercel.app"
    )


def test_cors_allows_public_vercel_origin_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BACKEND_CORS_ORIGINS", raising=False)

    with TestClient(create_app()) as client:
        response = client.options(
            "/api/v1/events",
            headers={
                "Origin": "https://hackathon-taws-track5.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://hackathon-taws-track5.vercel.app"
    )


def test_list_events_supports_filters(api_client) -> None:
    response = api_client.get("/api/v1/events", params={"asset": "AAPL"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["event"]["id"] == "evt_aapl_outlook_20260709"
    assert len(payload["data"][0]["articles"]) == 2
    assert len(payload["data"][0]["sources"]) == 2
    assert payload["meta"]["dataMode"] == "fixture"


def test_watchlist_demo_global(api_client) -> None:
    response = api_client.get("/api/v1/watchlists/demo-global")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == "watchlist_demo_global"
    assert payload["data"]["assetIds"] == ["ast_aapl", "ast_btc_usd", "ast_wti"]


def test_market_snapshots_endpoint_exposes_verifiable_observations(api_client) -> None:
    response = api_client.get("/api/v1/market-snapshots")

    assert response.status_code == 200
    payload = response.json()
    symbols = {snapshot["assetId"] for snapshot in payload["data"]}
    assert {"ast_aapl", "ast_spy", "ast_btc_usd", "ast_wti"} <= symbols
    assert payload["meta"]["dataMode"] == "fixture"
    assert all(len(snapshot["observations"]) >= 2 for snapshot in payload["data"])
    assert all(snapshot["contentHash"].startswith("sha256:") for snapshot in payload["data"])


def test_market_snapshots_endpoint_filters_by_asset_and_interval(api_client) -> None:
    response = api_client.get(
        "/api/v1/market-snapshots",
        params={"asset": "AAPL", "interval": "1d"},
    )

    assert response.status_code == 200
    snapshots = response.json()["data"]
    assert len(snapshots) == 1
    assert snapshots[0]["assetId"] == "ast_aapl"
    assert snapshots[0]["interval"] == "1d"
    first_observation = snapshots[0]["observations"][0]
    last_observation = snapshots[0]["observations"][-1]
    assert first_observation["timestamp"] < last_observation["timestamp"]


def test_instruments_endpoint_exposes_productive_universe(api_client) -> None:
    response = api_client.get("/api/v1/instruments")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 25
    symbols = {item["symbol"] for item in payload["data"]}
    assert {"AAPL", "MSFT", "NVDA", "QQQ", "ETH-USD", "WTI"} <= symbols
    assert payload["meta"]["provider"] == "production_universe_v1"


def test_instruments_endpoint_searches_symbol_and_name(api_client) -> None:
    response = api_client.get("/api/v1/instruments", params={"query": "micro"})

    assert response.status_code == 200
    assert [item["symbol"] for item in response.json()["data"]] == ["MSFT"]


def test_market_quotes_rejects_unknown_or_oversized_symbol_lists(api_client) -> None:
    unknown = api_client.get("/api/v1/market-quotes", params={"symbols": "UNKNOWN"})
    oversized = api_client.get(
        "/api/v1/market-quotes",
        params={"symbols": ",".join(["AAPL"] * 11)},
    )

    assert unknown.status_code == 422
    assert oversized.status_code == 200  # duplicates are normalized before enforcing the cap


def test_market_quotes_preserves_fixture_fallback(api_client) -> None:
    response = api_client.get(
        "/api/v1/market-quotes",
        params={"symbols": "AAPL,MSFT,ETH-USD"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["symbol"] for item in payload["data"]] == ["AAPL", "MSFT", "ETH-USD"]
    assert all(item["dataMode"] == "fallback" for item in payload["data"])
    assert payload["meta"]["dataMode"] == "fallback"


def test_similar_events_endpoint_exposes_deterministic_matches(api_client) -> None:
    response = api_client.get("/api/v1/events/evt_aapl_outlook_20260709/similar")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["dataMode"] == "fixture"
    assert payload["data"]
    scores = [item["similarityScore"] for item in payload["data"]]
    assert scores == sorted(scores, reverse=True)
    assert all(item["eventId"] != "evt_aapl_outlook_20260709" for item in payload["data"])
    assert all(item["rationale"] for item in payload["data"])


def test_ecuador_snapshots_are_traceable_and_hashed(api_client) -> None:
    response = api_client.get("/api/v1/ecuador-snapshots")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["dataMode"] == "fixture"
    assert len(payload["data"]) >= 2
    assert {item["countryCode"] for item in payload["data"]} == {"EC"}
    assert all(item["contentHash"].startswith("sha256:") for item in payload["data"])
    assert all(item["provider"] == "ecuador_institutional_snapshot" for item in payload["data"])


def test_get_signal_and_evidence_uses_runtime_metrics(api_client) -> None:
    signal_response = api_client.get("/api/v1/signals/sig_aapl_negative")
    evidence_response = api_client.get("/api/v1/signals/sig_aapl_negative/evidence")

    assert signal_response.status_code == 200
    signal = signal_response.json()["data"]
    assert signal["id"] == "sig_aapl_negative"
    assert signal["priceReaction"]["assetReturn"] == pytest.approx(-0.04)
    assert signal["priceReaction"]["benchmarkReturn"] == pytest.approx(-0.006)
    assert signal["priceReaction"]["abnormalReturn"] == pytest.approx(-0.034)
    assert signal["priceReaction"]["relativeVolume"] == pytest.approx(2.0)
    assert signal["analysisStatus"] == "completed"
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()["data"]) >= 1


def test_conversation_endpoints_preserve_context_and_messages(api_client) -> None:
    create_response = api_client.post(
        "/api/v1/conversations",
        json={"watchlistId": "watchlist_demo_global"},
    )
    assert create_response.status_code == 201
    conversation = create_response.json()["data"]
    assert conversation["summary"]
    assert conversation["watchlistId"] == "watchlist_demo_global"

    message_response = api_client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"content": "Explica la senal de AAPL con evidencia."},
    )
    loaded_response = api_client.get(f"/api/v1/conversations/{conversation['id']}")

    assert message_response.status_code == 201
    assert message_response.json()["data"]["role"] == "user"
    assert loaded_response.status_code == 200
    assert loaded_response.json()["data"]["messages"][0]["content"].startswith("Explica")


def test_conversation_response_persists_grounded_fixture_turn(api_client) -> None:
    conversation = api_client.post(
        "/api/v1/conversations",
        json={"watchlistId": "watchlist_demo_global"},
    ).json()["data"]

    response = api_client.post(
        f"/api/v1/conversations/{conversation['id']}/responses",
        json={"content": "Explica AAPL con evidencia verificable."},
    )
    loaded = api_client.get(f"/api/v1/conversations/{conversation['id']}").json()["data"]

    assert response.status_code == 201
    turn = response.json()["data"]
    assert turn["userMessage"]["role"] == "user"
    assert turn["assistantMessage"]["role"] == "assistant"
    assert turn["usedFallback"] is True
    assert turn["assistantMessage"]["metadata"]["dataMode"] == "fixture"
    assert turn["assistantMessage"]["metadata"]["signalId"] == "sig_aapl_negative"
    assert turn["assistantMessage"]["metadata"]["evidenceIds"]
    assert turn["context"] == {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "coverage": "signal",
        "dataMode": None,
    }
    assert loaded["activeInstrumentSymbol"] == "AAPL"
    assert [item["role"] for item in loaded["messages"]] == ["user", "assistant"]


def test_create_review_updates_signal_state(api_client) -> None:
    response = api_client.post(
        "/api/v1/signals/sig_btc_uncertain/reviews",
        headers={"Idempotency-Key": "review-btc-001"},
        json={"status": "escalated", "justification": "Requiere validacion humana adicional."},
    )
    signal_response = api_client.get("/api/v1/signals/sig_btc_uncertain")

    assert response.status_code == 201
    assert response.json()["data"][-1]["status"] == "escalated"
    assert signal_response.json()["data"]["review"]["status"] == "escalated"


def test_create_review_uses_authenticated_app_user() -> None:
    app = create_app()
    app.dependency_overrides[get_current_app_user] = lambda: AppUserContext(
        id="usr_senior",
        organization_id="org_demo",
        role="senior_analyst",
        display_name="Senior Analyst",
        is_active=True,
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/signals/sig_btc_uncertain/reviews",
            headers={"Idempotency-Key": "review-auth-user-001"},
            json={
                "status": "escalated",
                "justification": "Requiere validacion de un senior.",
            },
        )

    assert response.status_code == 201
    reviewer = response.json()["data"][-1]["reviewedBy"]
    assert reviewer == {"id": "usr_senior", "name": "Senior Analyst"}


def test_review_idempotency_replays_same_result(api_client) -> None:
    headers = {"Idempotency-Key": "review-idem-001"}
    payload = {
        "status": "escalated",
        "justification": "Se mantiene la misma revision.",
    }

    first_response = api_client.post(
        "/api/v1/signals/sig_wti_context/reviews",
        headers=headers,
        json=payload,
    )
    second_response = api_client.post(
        "/api/v1/signals/sig_wti_context/reviews",
        headers=headers,
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json() == second_response.json()


def test_review_idempotency_rejects_different_payload(api_client) -> None:
    headers = {"Idempotency-Key": "review-idem-002"}
    api_client.post(
        "/api/v1/signals/sig_wti_context/reviews",
        headers=headers,
        json={
            "status": "escalated",
            "justification": "Primera decision.",
        },
    )
    response = api_client.post(
        "/api/v1/signals/sig_wti_context/reviews",
        headers=headers,
        json={
            "status": "discarded",
            "justification": "Payload distinto.",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    assert "different review payload" in response.json()["message"]


def test_create_draft_briefing_includes_review_tasks(api_client) -> None:
    response = api_client.post(
        "/api/v1/briefings",
        headers={"Idempotency-Key": "briefing-001"},
        json={
            "watchlistId": "watchlist_demo_global",
            "signalIds": ["sig_aapl_negative", "sig_wti_context"],
            "status": "draft",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["data"]["status"] == "draft"
    assert len(payload["data"]["prioritizedSignals"]) == 2
    assert len(payload["data"]["reviewTasks"]) >= 2
    assert any(task["kind"] == "review" for task in payload["data"]["reviewTasks"])
    assert any(task["status"] == "open" for task in payload["data"]["reviewTasks"])


def test_shareable_briefing_rejects_pending_reviews(api_client) -> None:
    app = create_app()
    app.dependency_overrides[get_current_app_user] = lambda: AppUserContext(
        id="usr_senior",
        organization_id="org_demo",
        role="senior_analyst",
        display_name="Senior Analyst",
        is_active=True,
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/briefings",
            headers={"Idempotency-Key": "briefing-shareable-001"},
            json={
                "watchlistId": "watchlist_demo_global",
                "signalIds": ["sig_aapl_negative", "sig_wti_context"],
                "status": "shareable",
            },
        )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    assert "reviewed signals only" in response.json()["message"]


def test_analyst_cannot_create_shareable_briefing(api_client) -> None:
    response = api_client.post(
        "/api/v1/briefings",
        headers={"Idempotency-Key": "briefing-shareable-role-001"},
        json={
            "watchlistId": "watchlist_demo_global",
            "signalIds": ["sig_aapl_negative"],
            "status": "shareable",
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Shareable briefing not permitted"


def test_create_analysis_returns_processing_and_streams_steps(api_client) -> None:
    response = api_client.post(
        "/api/v1/analyses",
        headers={"Idempotency-Key": "analysis-001"},
        json={
            "eventId": "evt_aapl_outlook_20260709",
            "assetIds": ["ast_aapl"],
        },
    )

    assert response.status_code == 202
    run_id = response.json()["data"]["id"]
    assert response.json()["data"]["status"] == "processing"

    terminal_run = _wait_for_terminal_run(api_client, run_id)
    steps_response = api_client.get(f"/api/v1/runs/{run_id}/steps")
    stream_response = api_client.get(f"/api/v1/analyses/{run_id}/stream")

    assert terminal_run["status"] == "completed"
    assert steps_response.status_code == 200
    assert len(steps_response.json()["data"]) == 13
    assert stream_response.status_code == 200
    assert ": heartbeat" in stream_response.text
    assert "analysis-step" in stream_response.text
    assert "verify_sources" in stream_response.text
    assert "risk_language_guard" in stream_response.text


def test_analysis_idempotency_replays_same_run(api_client) -> None:
    headers = {"Idempotency-Key": "analysis-idem-001"}
    payload = {
        "eventId": "evt_aapl_outlook_20260709",
        "assetIds": ["ast_aapl"],
    }

    first_response = api_client.post("/api/v1/analyses", headers=headers, json=payload)
    second_response = api_client.post("/api/v1/analyses", headers=headers, json=payload)

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert first_response.json()["data"]["id"] == second_response.json()["data"]["id"]


def test_analysis_idempotency_rejects_different_payload(api_client) -> None:
    headers = {"Idempotency-Key": "analysis-idem-002"}
    api_client.post(
        "/api/v1/analyses",
        headers=headers,
        json={
            "eventId": "evt_aapl_outlook_20260709",
            "assetIds": ["ast_aapl"],
        },
    )
    response = api_client.post(
        "/api/v1/analyses",
        headers=headers,
        json={
            "eventId": "evt_btc_policy_20260710",
            "assetIds": ["ast_btc_usd"],
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    assert "different analysis payload" in response.json()["message"]


def test_analysis_stream_supports_last_event_id_replay(api_client) -> None:
    response = api_client.post(
        "/api/v1/analyses",
        headers={"Idempotency-Key": "analysis-002"},
        json={
            "eventId": "evt_btc_policy_20260710",
            "assetIds": ["ast_btc_usd"],
        },
    )
    run_id = response.json()["data"]["id"]
    _wait_for_terminal_run(api_client, run_id)
    steps = api_client.get(f"/api/v1/runs/{run_id}/steps").json()["data"]
    stream_response = api_client.get(
        f"/api/v1/analyses/{run_id}/stream",
        headers={"Last-Event-ID": steps[4]["id"]},
    )

    assert stream_response.status_code == 200
    assert steps[0]["id"] not in stream_response.text
    assert steps[5]["id"] in stream_response.text


def test_analysis_stream_supports_eventsource_query_replay(api_client) -> None:
    response = api_client.post(
        "/api/v1/analyses",
        headers={"Idempotency-Key": "analysis-003"},
        json={
            "eventId": "evt_btc_policy_20260710",
            "assetIds": ["ast_btc_usd"],
        },
    )
    run_id = response.json()["data"]["id"]
    _wait_for_terminal_run(api_client, run_id)
    steps = api_client.get(f"/api/v1/runs/{run_id}/steps").json()["data"]
    stream_response = api_client.get(
        f"/api/v1/analyses/{run_id}/stream",
        params={"lastEventId": steps[4]["id"]},
    )

    assert stream_response.status_code == 200
    assert steps[0]["id"] not in stream_response.text
    assert steps[5]["id"] in stream_response.text


def test_api_errors_follow_api_error_shape(api_client) -> None:
    response = api_client.get("/api/v1/signals/sig_missing")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "sig_missing",
    }
