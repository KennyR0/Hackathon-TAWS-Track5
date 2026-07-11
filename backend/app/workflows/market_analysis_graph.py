"""LangGraph workflow for fixture-first market analyses."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.contracts.api import AgentRunStep
from app.contracts.entities import Signal, allow_internal_field_names
from app.llm.base import LLMAdapter
from app.repositories.fixture_repository import FixtureRepository
from app.workflows.state import MarketAnalysisState


def run_market_analysis_workflow(
    *,
    repository: FixtureRepository,
    llm_adapter: LLMAdapter,
    run_id: str,
    event_id: str,
    asset_ids: tuple[str, ...],
) -> tuple[Signal, ...]:
    graph = StateGraph(MarketAnalysisState)
    for node_name, handler in (
        ("load_context", _load_context(repository)),
        ("normalize_news", _passthrough_node("normalize_news")),
        ("link_assets", _passthrough_node("link_assets")),
        ("fetch_market_snapshots", _passthrough_node("fetch_market_snapshots")),
        ("calculate_reactions", _calculate_reactions(repository)),
        ("analyst_agent", _analyst_agent(llm_adapter)),
        ("validate_evidence", _validate_evidence(repository)),
        ("abstention_guard", _passthrough_node("abstention_guard")),
        ("advisor_agent", _advisor_agent(llm_adapter)),
        ("briefing_builder", _passthrough_node("briefing_builder")),
        ("audit_writer", _passthrough_node("audit_writer")),
    ):
        graph.add_node(node_name, handler)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "normalize_news")
    graph.add_edge("normalize_news", "link_assets")
    graph.add_edge("link_assets", "fetch_market_snapshots")
    graph.add_edge("fetch_market_snapshots", "calculate_reactions")
    graph.add_edge("calculate_reactions", "analyst_agent")
    graph.add_edge("analyst_agent", "validate_evidence")
    graph.add_edge("validate_evidence", "abstention_guard")
    graph.add_edge("abstention_guard", "advisor_agent")
    graph.add_edge("advisor_agent", "briefing_builder")
    graph.add_edge("briefing_builder", "audit_writer")
    graph.add_edge("audit_writer", END)

    state: MarketAnalysisState = {
        "run_id": run_id,
        "request_event_id": event_id,
        "asset_ids": asset_ids,
        "warnings": [],
        "steps": [],
        "payloads": {},
        "fixture_clock": repository.fixture_clock.isoformat(),
    }
    compiled = graph.compile()
    final_state = compiled.invoke(state)
    repository.set_run_steps(run_id, tuple(final_state["steps"]))
    return final_state["matched_signals"]


def _load_context(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        event, _ = repository.get_event(state["request_event_id"])
        matched_signals = repository.find_signals_for_event_assets(
            event_id=event.id,
            asset_ids=state["asset_ids"],
        )
        state["event"] = event
        state["matched_signals"] = matched_signals
        _append_step(state, "load_context", {"eventId": event.id, "signalCount": len(matched_signals)})
        return state

    return handler


def _passthrough_node(node_name: str):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        _append_step(state, node_name, {"status": "ok"})
        return state

    return handler


def _calculate_reactions(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload: dict[str, Any] = {}
        enriched_signals: list[Signal] = []
        for signal in state["matched_signals"]:
            price_reaction = signal.price_reaction or repository.calculate_signal_price_reaction(signal)
            if price_reaction is not None:
                signal = signal.model_copy(update={"price_reaction": price_reaction})
            enriched_signals.append(signal)
            payload[signal.id] = signal.price_reaction.model_dump(mode="json", by_alias=True) if signal.price_reaction else {}
        state["matched_signals"] = tuple(enriched_signals)
        state["payloads"]["calculate_reactions"] = payload
        _append_step(state, "calculate_reactions", payload)
        return state

    return handler


def _analyst_agent(llm_adapter: LLMAdapter):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        summaries = {
            signal.id: llm_adapter.summarize_signal(signal)
            for signal in state["matched_signals"]
        }
        state["result_summary"] = " | ".join(summaries.values())
        state["payloads"]["analyst_agent"] = summaries
        _append_step(state, "analyst_agent", summaries)
        return state

    return handler


def _validate_evidence(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload = {}
        for signal in state["matched_signals"]:
            evidence = repository.get_signal_evidence(signal.id)
            payload[signal.id] = {
                "evidenceCount": len(evidence),
                "counterEvidenceCount": len(
                    tuple(item for item in evidence if not item.supports_signal)
                ),
            }
        state["evidence_checked"] = True
        state["payloads"]["validate_evidence"] = payload
        _append_step(state, "validate_evidence", payload)
        return state

    return handler


def _advisor_agent(llm_adapter: LLMAdapter):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        summary = llm_adapter.build_briefing_summary(state["matched_signals"])
        state["advisor_summary"] = summary
        _append_step(state, "advisor_agent", {"summary": summary})
        return state

    return handler


def _append_step(state: MarketAnalysisState, node: str, payload: dict[str, Any]) -> None:
    sequence = len(state["steps"]) + 1
    timestamp = _step_timestamp(state["fixture_clock"], sequence)
    with allow_internal_field_names():
        state["steps"].append(
            AgentRunStep(
                id=f"step_{state['run_id']}_{sequence:03d}",
                run_id=state["run_id"],
                node=node,
                status="completed",
                timestamp=timestamp,
                payload=payload,
            )
        )
    state["current_node"] = node


def _step_timestamp(fixture_clock: str, sequence: int):
    from datetime import datetime

    return datetime.fromisoformat(fixture_clock) + timedelta(seconds=sequence)
