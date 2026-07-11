from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.request
from collections.abc import Iterator
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from statistics import fmean
from typing import Any

import pytest
from conftest import BACKEND_ROOT
from pydantic import BaseModel, ValidationError

from app.contracts.entities import Article, DataMode, MarketSnapshot
from app.contracts.fixtures import (
    FixtureBundle,
    build_fixture_hash,
    calculation_evidence_hash_payload,
    load_fixture_bundle,
    market_snapshot_hash_payload,
    sha256_digest,
)

REPO_ROOT = BACKEND_ROOT.parent
BUNDLE_PATH = REPO_ROOT / "data" / "fixtures" / "v1" / "phase0_bundle.json"
GENERATOR_PATH = BACKEND_ROOT / "scripts" / "generate_fixtures.py"


@pytest.fixture(scope="module")
def phase0_bundle() -> FixtureBundle:
    return load_fixture_bundle(BUNDLE_PATH)


@pytest.fixture
def wire_bundle() -> dict[str, Any]:
    return json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def _all_datetimes(value: object) -> Iterator[datetime]:
    if isinstance(value, datetime):
        yield value
    elif isinstance(value, BaseModel):
        yield from _all_datetimes(value.model_dump(mode="python"))
    elif isinstance(value, dict):
        for child in value.values():
            yield from _all_datetimes(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _all_datetimes(child)


def _all_keys(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def _snapshot_by_symbol(phase0_bundle: FixtureBundle, symbol: str) -> MarketSnapshot:
    asset = next(item for item in phase0_bundle.assets if item.symbol == symbol)
    return next(item for item in phase0_bundle.market_snapshots if item.asset_id == asset.id)


def test_bundle_loads_with_all_phase0_entities(phase0_bundle: FixtureBundle) -> None:
    collections = {
        "Source": phase0_bundle.sources,
        "Article": phase0_bundle.articles,
        "Event": phase0_bundle.events,
        "Asset": phase0_bundle.assets,
        "MarketSnapshot": phase0_bundle.market_snapshots,
        "Claim": phase0_bundle.claims,
        "Evidence": phase0_bundle.evidence,
        "Signal": phase0_bundle.signals,
        "SignalReview": phase0_bundle.signal_reviews,
        "Briefing": phase0_bundle.briefings,
        "AgentRun": phase0_bundle.agent_runs,
    }
    assert all(collections.values()), f"Empty Phase 0 entity collections: {collections}"
    assert len(phase0_bundle.raw_source_snapshots) == 6
    assert phase0_bundle.manifest.fixture_clock.isoformat() == "2026-07-11T13:00:00+00:00"


def test_corpus_covers_aapl_spy_btc_and_wti(phase0_bundle: FixtureBundle) -> None:
    assert {item.symbol for item in phase0_bundle.assets} == {
        "AAPL",
        "SPY",
        "BTC-USD",
        "WTI",
    }
    assert {item.id for item in phase0_bundle.events} == {
        "evt_aapl_outlook_20260709",
        "evt_btc_policy_20260710",
        "evt_wti_supply_20260710",
    }
    assert {item.id for item in phase0_bundle.signals} == {
        "sig_aapl_negative",
        "sig_btc_uncertain",
        "sig_wti_context",
    }
    assert len(phase0_bundle.articles) == 6
    assert len(phase0_bundle.signal_reviews) >= 1


def test_aapl_spy_metrics_are_reproducible(phase0_bundle: FixtureBundle) -> None:
    aapl = _snapshot_by_symbol(phase0_bundle, "AAPL")
    spy = _snapshot_by_symbol(phase0_bundle, "SPY")
    aapl_return = aapl.observations[-1].close / aapl.observations[-2].close - 1
    spy_return = spy.observations[-1].close / spy.observations[-2].close - 1
    abnormal_return = aapl_return - spy_return
    prior_volumes = [point.volume for point in aapl.observations[-21:-1]]

    assert len(prior_volumes) == 20
    assert all(volume is not None for volume in prior_volumes)
    current_volume = aapl.observations[-1].volume
    assert current_volume is not None
    relative_volume = current_volume / fmean(
        volume for volume in prior_volumes if volume is not None
    )
    assert aapl_return == pytest.approx(-0.04)
    assert spy_return == pytest.approx(-0.006)
    assert abnormal_return == pytest.approx(-0.034)
    assert relative_volume == pytest.approx(2.0)

    signal = next(item for item in phase0_bundle.signals if item.id == "sig_aapl_negative")
    assert signal.price_reaction is not None
    assert signal.price_reaction.asset_return == pytest.approx(aapl_return)
    assert signal.price_reaction.benchmark_return == pytest.approx(spy_return)
    assert signal.price_reaction.abnormal_return == pytest.approx(abnormal_return)
    assert signal.price_reaction.relative_volume == pytest.approx(relative_volume)


def test_btc_and_wti_metrics_are_reproducible(phase0_bundle: FixtureBundle) -> None:
    btc = _snapshot_by_symbol(phase0_bundle, "BTC-USD")
    wti = _snapshot_by_symbol(phase0_bundle, "WTI")
    btc_return = btc.observations[-1].close / btc.observations[-2].close - 1
    wti_return = wti.observations[-1].close / wti.observations[0].close - 1

    assert btc.end_at - btc.start_at >= timedelta(days=30)
    assert btc.observations[-1].timestamp - btc.observations[-2].timestamp == timedelta(days=1)
    assert btc_return == pytest.approx(0.02)
    assert wti.end_at - wti.start_at >= timedelta(days=30)
    assert wti.missing_value_policy == "skip_non_trading_days"
    assert wti_return == pytest.approx(0.07)

    expected_claim_values = {
        "clm_aapl_asset_return": -0.04,
        "clm_aapl_benchmark_return": -0.006,
        "clm_aapl_abnormal_return": -0.034,
        "clm_aapl_relative_volume": 2.0,
        "clm_btc_24h_return": 0.02,
        "clm_wti_30d_change": 0.07,
    }
    actual_claim_values = {
        claim.id: claim.numeric_value
        for claim in phase0_bundle.claims
        if claim.id in expected_claim_values
    }
    assert actual_claim_values == expected_claim_values


def test_each_event_has_two_independent_test_publishers(
    phase0_bundle: FixtureBundle,
) -> None:
    sources = {item.id: item for item in phase0_bundle.sources}
    articles = {item.id: item for item in phase0_bundle.articles}
    assert all(source.domain.endswith(".test") for source in sources.values())

    for event in phase0_bundle.events:
        event_sources = [
            sources[articles[article_id].source_id] for article_id in event.article_ids
        ]
        assert len(event_sources) >= 2
        assert all(source.is_original_publisher for source in event_sources)
        assert all(not source.is_aggregator for source in event_sources)
        assert len({source.publisher_group_id for source in event_sources}) >= 2


def test_claim_evidence_source_snapshot_trace_is_complete(
    phase0_bundle: FixtureBundle,
) -> None:
    sources = {item.id: item for item in phase0_bundle.sources}
    articles = {item.id: item for item in phase0_bundle.articles}
    events = {item.id: item for item in phase0_bundle.events}
    snapshots = {item.id: item for item in phase0_bundle.market_snapshots}
    claims = {item.id: item for item in phase0_bundle.claims}
    evidence = {item.id: item for item in phase0_bundle.evidence}
    signals = {item.id: item for item in phase0_bundle.signals}
    raw_snapshots = {item.id: item for item in phase0_bundle.raw_source_snapshots}

    for claim in claims.values():
        assert claim.event_id in events
        assert claim.signal_id in signals
        assert signals[claim.signal_id].event_id == claim.event_id
        for evidence_id in (*claim.evidence_ids, *claim.counter_evidence_ids):
            item = evidence[evidence_id]
            assert item.claim_id == claim.id
            assert item.signal_id == claim.signal_id

    for item in evidence.values():
        claim = claims[item.claim_id]
        assert item.claim == claim.claim
        if item.evidence_type == "source":
            assert item.article_id is not None
            assert item.source_id is not None
            assert item.source_snapshot_id is not None
            article = articles[item.article_id]
            source = sources[item.source_id]
            raw_snapshot = raw_snapshots[item.source_snapshot_id]
            assert article.source_id == source.id == raw_snapshot.source_id
            assert article.source_snapshot_id == raw_snapshot.id
            assert item.content_hash == article.content_hash == raw_snapshot.content_hash
        else:
            assert item.market_snapshot_ids
            assert all(snapshot_id in snapshots for snapshot_id in item.market_snapshot_ids)

    claim_evidence_ids = {
        evidence_id
        for claim in claims.values()
        for evidence_id in (*claim.evidence_ids, *claim.counter_evidence_ids)
    }
    signal_evidence_ids = {
        evidence_id
        for signal in signals.values()
        for evidence_id in (*signal.evidence_ids, *signal.counter_evidence_ids)
    }
    assert set(evidence) == claim_evidence_ids == signal_evidence_ids


def test_remaining_cross_entity_references_are_resolved(
    phase0_bundle: FixtureBundle,
) -> None:
    assets = {item.id for item in phase0_bundle.assets}
    signals = {item.id for item in phase0_bundle.signals}
    snapshot_ids = {
        *(item.id for item in phase0_bundle.market_snapshots),
        *(item.id for item in phase0_bundle.raw_source_snapshots),
    }

    for event in phase0_bundle.events:
        assert all(relation.asset_id in assets for relation in event.related_assets)
    for review in phase0_bundle.signal_reviews:
        assert review.signal_id in signals
    for briefing in phase0_bundle.briefings:
        assert {item.signal_id for item in briefing.prioritized_signals} == signals
    for run in phase0_bundle.agent_runs:
        assert set(run.source_snapshot_ids) <= snapshot_ids


def test_provenance_uses_fixture_mode_and_fixed_clock(
    phase0_bundle: FixtureBundle,
) -> None:
    provenance_items = (
        *phase0_bundle.articles,
        *phase0_bundle.events,
        *phase0_bundle.market_snapshots,
    )
    for item in provenance_items:
        assert item.data_mode is DataMode.FIXTURE
        assert item.provider
        assert item.retrieved_at <= phase0_bundle.manifest.fixture_clock
        assert item.data_as_of <= item.retrieved_at
        assert item.freshness.evaluated_at == phase0_bundle.manifest.fixture_clock
        assert item.warnings


def test_all_fixture_dates_are_at_or_before_fixture_clock(
    phase0_bundle: FixtureBundle,
) -> None:
    timestamps = tuple(_all_datetimes(phase0_bundle))
    assert timestamps
    assert all(timestamp.tzinfo is not None for timestamp in timestamps)
    assert max(timestamps) <= phase0_bundle.manifest.fixture_clock


def test_all_hashes_match_canonical_payloads(phase0_bundle: FixtureBundle) -> None:
    claims = {item.id: item for item in phase0_bundle.claims}
    snapshots = {item.id: item for item in phase0_bundle.market_snapshots}
    raw_snapshots = {item.id: item for item in phase0_bundle.raw_source_snapshots}

    for raw_snapshot in raw_snapshots.values():
        assert raw_snapshot.content_hash == sha256_digest(raw_snapshot.payload)
    for snapshot in snapshots.values():
        assert snapshot.content_hash == sha256_digest(market_snapshot_hash_payload(snapshot))
    for item in phase0_bundle.evidence:
        if item.evidence_type == "source":
            assert item.source_snapshot_id is not None
            assert item.content_hash == raw_snapshots[item.source_snapshot_id].content_hash
        elif item.evidence_type in {"market_data", "context"}:
            assert len(item.market_snapshot_ids) == 1
            assert item.content_hash == snapshots[item.market_snapshot_ids[0]].content_hash
        else:
            assert item.content_hash == sha256_digest(
                calculation_evidence_hash_payload(item, claims[item.claim_id])
            )
    assert phase0_bundle.manifest.fixture_hash == build_fixture_hash(phase0_bundle)


def test_raw_snapshot_payload_tampering_is_rejected(wire_bundle: dict[str, Any]) -> None:
    tampered = deepcopy(wire_bundle)
    tampered["rawSourceSnapshots"][0]["payload"]["headline"] += " alterado"
    with pytest.raises(ValidationError, match="raw source snapshot contentHash"):
        FixtureBundle.model_validate(tampered)


def test_market_snapshot_tampering_is_rejected(wire_bundle: dict[str, Any]) -> None:
    tampered = deepcopy(wire_bundle)
    tampered["marketSnapshots"][0]["observations"][-1]["close"] = 999.0
    with pytest.raises(ValidationError, match="market snapshot contentHash is invalid"):
        FixtureBundle.model_validate(tampered)


def test_calculation_claim_tampering_is_rejected(wire_bundle: dict[str, Any]) -> None:
    tampered = deepcopy(wire_bundle)
    claim = next(item for item in tampered["claims"] if item["id"] == "clm_aapl_abnormal_return")
    claim["numericValue"] = -0.035
    with pytest.raises(ValidationError, match="market/calculation evidence contentHash is invalid"):
        FixtureBundle.model_validate(tampered)


def test_manifest_hash_tampering_is_rejected(wire_bundle: dict[str, Any]) -> None:
    tampered = deepcopy(wire_bundle)
    tampered["manifest"]["fixtureHash"] = f"sha256:{'0' * 64}"
    with pytest.raises(ValidationError, match="fixture manifest hash"):
        FixtureBundle.model_validate(tampered)


def test_wire_document_uses_only_camel_case_aliases(wire_bundle: dict[str, Any]) -> None:
    assert "marketSnapshots" in wire_bundle
    assert "rawSourceSnapshots" in wire_bundle
    assert "signalReviews" in wire_bundle
    assert not [key for key in _all_keys(wire_bundle) if "_" in key]

    canonical_article = wire_bundle["articles"][0]
    assert Article.model_validate(canonical_article).source_id == canonical_article["sourceId"]
    snake_case_article = deepcopy(canonical_article)
    snake_case_article["source_id"] = snake_case_article.pop("sourceId")
    with pytest.raises(ValidationError, match="source_id"):
        Article.model_validate(snake_case_article)


def test_extra_fields_are_rejected_at_root_and_nested_levels(
    wire_bundle: dict[str, Any],
) -> None:
    nested_extra = deepcopy(wire_bundle)
    nested_extra["articles"][0]["consumerGuess"] = "not declared"
    with pytest.raises(ValidationError, match="consumerGuess"):
        FixtureBundle.model_validate(nested_extra)

    root_extra = deepcopy(wire_bundle)
    root_extra["consumerGuess"] = "not declared"
    with pytest.raises(ValidationError, match="consumerGuess"):
        FixtureBundle.model_validate(root_extra)


def test_bundle_load_is_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("fixture loading attempted network access")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(urllib.request, "urlopen", reject_network)
    bundle = load_fixture_bundle(BUNDLE_PATH)
    assert bundle.manifest.fixture_id == "fixture_phase0_v1"


def test_generator_is_byte_identical_and_matches_committed_bundle(tmp_path: Path) -> None:
    generated_paths = (tmp_path / "seed-1.json", tmp_path / "seed-987654.json")
    for hash_seed, output in zip(("1", "987654"), generated_paths, strict=True):
        environment = os.environ.copy()
        environment.update({"PYTHONHASHSEED": hash_seed, "PYTHONUTF8": "1"})
        completed = subprocess.run(
            [sys.executable, str(GENERATOR_PATH), "--output", str(output)],
            cwd=REPO_ROOT,
            env=environment,
            check=True,
            capture_output=True,
        )
        assert b"Generated" in completed.stdout

    assert generated_paths[0].read_bytes() == generated_paths[1].read_bytes()
    assert generated_paths[0].read_bytes() == BUNDLE_PATH.read_bytes()
