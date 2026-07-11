from __future__ import annotations


def test_health_endpoint(api_client) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "nexomercado-api",
        "contractVersion": "0.1.0",
    }


def test_list_events_supports_filters(api_client) -> None:
    response = api_client.get("/api/v1/events", params={"asset": "AAPL"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["event"]["id"] == "evt_aapl_outlook_20260709"
    assert payload["meta"]["dataMode"] == "fixture"


def test_watchlist_demo_global(api_client) -> None:
    response = api_client.get("/api/v1/watchlists/demo-global")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == "watchlist_demo_global"
    assert payload["data"]["assetIds"] == ["ast_aapl", "ast_btc_usd", "ast_wti"]


def test_get_signal_and_evidence(api_client) -> None:
    signal_response = api_client.get("/api/v1/signals/sig_aapl_negative")
    evidence_response = api_client.get("/api/v1/signals/sig_aapl_negative/evidence")

    assert signal_response.status_code == 200
    assert signal_response.json()["data"]["id"] == "sig_aapl_negative"
    assert evidence_response.status_code == 200
    assert len(evidence_response.json()["data"]) >= 1


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
    assert "different review payload" in response.json()["detail"]


def test_create_draft_briefing(api_client) -> None:
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


def test_shareable_briefing_rejects_pending_reviews(api_client) -> None:
    response = api_client.post(
        "/api/v1/briefings",
        headers={"Idempotency-Key": "briefing-shareable-001"},
        json={
            "watchlistId": "watchlist_demo_global",
            "signalIds": ["sig_aapl_negative", "sig_btc_uncertain"],
            "status": "shareable",
        },
    )

    assert response.status_code == 409
    assert "reviewed signals only" in response.json()["detail"]


def test_create_analysis_and_stream_steps(api_client) -> None:
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

    steps_response = api_client.get(f"/api/v1/runs/{run_id}/steps")
    stream_response = api_client.get(f"/api/v1/analyses/{run_id}/stream")

    assert steps_response.status_code == 200
    assert len(steps_response.json()["data"]) == 11
    assert stream_response.status_code == 200
    assert ": heartbeat" in stream_response.text
    assert "analysis-step" in stream_response.text


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
    assert first_response.json() == second_response.json()


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
    assert "different analysis payload" in response.json()["detail"]


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
    steps = api_client.get(f"/api/v1/runs/{run_id}/steps").json()["data"]
    stream_response = api_client.get(
        f"/api/v1/analyses/{run_id}/stream",
        headers={"Last-Event-ID": steps[4]["id"]},
    )

    assert stream_response.status_code == 200
    assert steps[0]["id"] not in stream_response.text
    assert steps[5]["id"] in stream_response.text
