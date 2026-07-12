"""Workflow state definitions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from app.contracts.api import AgentRunStep
from app.contracts.entities import Article, Event, MarketSnapshot, Signal, Source
from app.llm.base import BriefingSummaryOutput, SignalAnalysisOutput


class MarketAnalysisState(TypedDict, total=False):
    run_id: str
    request_event_id: str
    asset_ids: tuple[str, ...]
    fixture_clock: str
    run_started_at: str
    current_node: str
    event: Event
    event_articles: tuple[Article, ...]
    event_sources: tuple[Source, ...]
    market_snapshots: tuple[MarketSnapshot, ...]
    normalized_articles: tuple[dict[str, Any], ...]
    source_validation: dict[str, Any]
    matched_signals: tuple[Signal, ...]
    advisor_signals: tuple[Signal, ...]
    warnings: list[str]
    steps: list[AgentRunStep]
    analyst_outputs: dict[str, SignalAnalysisOutput]
    advisor_summary: BriefingSummaryOutput
    evidence_checked: bool
    payloads: dict[str, dict[str, Any]]
    step_sink: Callable[[AgentRunStep], None]
