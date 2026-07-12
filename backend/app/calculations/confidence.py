"""Confidence scoring helpers."""

from __future__ import annotations

from app.contracts.entities import AnalysisStatus, Impact


def apply_confidence_penalties(
    base_confidence: float,
    *,
    has_single_source: bool = False,
    has_material_contradiction: bool = False,
    has_incomplete_history: bool = False,
    has_old_fallback: bool = False,
    has_indirect_relation: bool = False,
) -> float:
    confidence = base_confidence
    if has_single_source:
        confidence -= 0.20
    if has_material_contradiction:
        confidence -= 0.20
    if has_incomplete_history:
        confidence -= 0.15
    if has_old_fallback:
        confidence -= 0.10
    if has_indirect_relation:
        confidence -= 0.10
    return max(0.0, min(1.0, confidence))


def derive_safe_status(impact: Impact, confidence: float) -> tuple[Impact, AnalysisStatus]:
    if confidence < 0.60:
        return Impact.UNCERTAIN, AnalysisStatus.INSUFFICIENT_EVIDENCE
    return impact, AnalysisStatus.COMPLETED
