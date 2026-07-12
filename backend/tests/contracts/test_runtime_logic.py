from __future__ import annotations

import pytest

from app.api import dependencies
from app.calculations.confidence import apply_confidence_penalties, derive_safe_status
from app.calculations.returns import compute_asset_return, compute_benchmark_return, compute_relative_volume
from app.contracts.entities import AnalysisStatus, Impact
from app.workflows.market_analysis_graph import sanitize_risk_language


def test_event_source_diagnostics_counts_independent_publishers() -> None:
    repository = dependencies.get_repository()

    diagnostics = repository.get_event_source_diagnostics("evt_aapl_outlook_20260709")

    assert diagnostics["independentPublisherCount"] == 2
    assert diagnostics["sourceCount"] == 2
    assert diagnostics["warnings"] == []


def test_runtime_signal_recomputes_market_metrics() -> None:
    repository = dependencies.get_repository()

    signal = repository.build_runtime_signal("sig_aapl_negative")

    assert signal.price_reaction is not None
    assert signal.price_reaction.asset_return == pytest.approx(-0.04)
    assert signal.price_reaction.benchmark_return == pytest.approx(-0.006)
    assert signal.price_reaction.abnormal_return == pytest.approx(-0.034)
    assert signal.price_reaction.relative_volume == pytest.approx(2.0)
    assert signal.analysis_status == AnalysisStatus.COMPLETED


def test_runtime_signal_abstains_under_material_contradiction() -> None:
    repository = dependencies.get_repository()

    signal = repository.build_runtime_signal("sig_btc_uncertain")

    assert signal.impact == Impact.UNCERTAIN
    assert signal.analysis_status == AnalysisStatus.INSUFFICIENT_EVIDENCE
    assert signal.confidence < 0.60


def test_price_helpers_cover_benchmark_and_relative_volume() -> None:
    repository = dependencies.get_repository()
    event, _ = repository.get_event("evt_aapl_outlook_20260709")
    snapshots = repository.get_event_market_snapshots(event)
    asset_snapshot = next(item for item in snapshots if item.asset_id == "ast_aapl")
    benchmark_snapshot = next(item for item in repository._bundle.market_snapshots if item.asset_id == "ast_spy")

    assert compute_asset_return(asset_snapshot) == pytest.approx(-0.04)
    assert compute_benchmark_return(
        asset_snapshot=asset_snapshot,
        benchmark_snapshot=benchmark_snapshot,
    ) == pytest.approx(-0.006)
    assert compute_relative_volume(asset_snapshot) == pytest.approx(2.0)


def test_confidence_helpers_apply_penalties_and_abstention() -> None:
    confidence = apply_confidence_penalties(
        0.78,
        has_material_contradiction=True,
    )
    impact, status = derive_safe_status(Impact.POSITIVE, confidence)

    assert confidence == pytest.approx(0.58)
    assert impact == Impact.UNCERTAIN
    assert status == AnalysisStatus.INSUFFICIENT_EVIDENCE


def test_risk_language_guard_blocks_prohibited_language() -> None:
    sanitized, violations = sanitize_risk_language(
        "Compra esta accion, definitivamente subira y garantiza resultados."
    )

    assert sanitized.startswith("Resumen bloqueado")
    assert "compra" in violations
    assert "definitivamente" in violations
