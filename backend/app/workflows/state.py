"""Workflow state definitions."""

from __future__ import annotations

from typing import Any, TypedDict

from app.contracts.api import AgentRunStep
from app.contracts.entities import Event, Signal


class MarketAnalysisState(TypedDict, total=False):
    run_id: str
    request_event_id: str
    asset_ids: tuple[str, ...]
    fixture_clock: str
    current_node: str
    event: Event
    matched_signals: tuple[Signal, ...]
    warnings: list[str]
    steps: list[AgentRunStep]
    result_summary: str
    advisor_summary: str
    evidence_checked: bool
    payloads: dict[str, dict[str, Any]]
