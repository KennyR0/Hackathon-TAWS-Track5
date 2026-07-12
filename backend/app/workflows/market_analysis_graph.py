"""LangGraph workflow for fixture-first market analyses."""

from __future__ import annotations

from datetime import datetime, timedelta
from time import sleep
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.contracts.api import AgentRunStep
from app.contracts.entities import AnalysisStatus, Impact, Signal, allow_internal_field_names
from app.llm.base import LLMAdapter
from app.repositories.fixture_repository import FixtureRepository
from app.workflows.state import MarketAnalysisState

FORBIDDEN_LANGUAGE = (
    "compra",
    "comprar",
    "buy",
    "vende",
    "vender",
    "sell",
    "garantiza",
    "garantizado",
    "definitivamente",
)


def run_market_analysis_workflow(
    *,
    repository: FixtureRepository,
    llm_adapter: LLMAdapter,
    run_id: str,
    event_id: str,
    asset_ids: tuple[str, ...],
    started_at: datetime,
    step_sink,
) -> tuple[Signal, ...]:
    graph = StateGraph(MarketAnalysisState)
    for node_name, handler in (
        ("load_context", _load_context(repository)),
        ("normalize_news", _normalize_news(repository)),
        ("verify_sources", _verify_sources(repository)),
        ("link_assets", _link_assets(repository)),
        ("fetch_market_snapshots", _fetch_market_snapshots()),
        ("calculate_reactions", _calculate_reactions(repository)),
        ("analyst_agent", _analyst_agent(llm_adapter)),
        ("validate_evidence", _validate_evidence(repository)),
        ("abstention_guard", _abstention_guard()),
        ("advisor_agent", _advisor_agent(llm_adapter)),
        ("risk_language_guard", _risk_language_guard()),
        ("briefing_builder", _briefing_builder()),
        ("audit_writer", _audit_writer()),
    ):
        graph.add_node(node_name, handler)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "normalize_news")
    graph.add_edge("normalize_news", "verify_sources")
    graph.add_edge("verify_sources", "link_assets")
    graph.add_edge("link_assets", "fetch_market_snapshots")
    graph.add_edge("fetch_market_snapshots", "calculate_reactions")
    graph.add_edge("calculate_reactions", "analyst_agent")
    graph.add_edge("analyst_agent", "validate_evidence")
    graph.add_edge("validate_evidence", "abstention_guard")
    graph.add_edge("abstention_guard", "advisor_agent")
    graph.add_edge("advisor_agent", "risk_language_guard")
    graph.add_edge("risk_language_guard", "briefing_builder")
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
        "run_started_at": started_at.isoformat(),
        "step_sink": step_sink,
    }
    compiled = graph.compile()
    final_state = compiled.invoke(state)
    return final_state["matched_signals"]


def sanitize_risk_language(text: str) -> tuple[str, tuple[str, ...]]:
    lower_text = text.lower()
    violations = tuple(token for token in FORBIDDEN_LANGUAGE if token in lower_text)
    if not violations:
        return text, ()
    safe_text = (
        "Resumen bloqueado por lenguaje de riesgo. "
        "Se reemplazo por una version prudente sujeta a revision humana."
    )
    return safe_text, violations


def _load_context(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        event, _ = repository.get_event(state["request_event_id"])
        event_articles = repository.get_event_articles(event.id)
        event_sources = repository.get_event_sources(event.id)
        market_snapshots = repository.get_event_market_snapshots(event)
        matched_signals = repository.find_signals_for_event_assets(
            event_id=event.id,
            asset_ids=state["asset_ids"],
        )
        state["event"] = event
        state["event_articles"] = event_articles
        state["event_sources"] = event_sources
        state["market_snapshots"] = market_snapshots
        state["matched_signals"] = matched_signals
        _append_step(
            state,
            "load_context",
            {
                "eventId": event.id,
                "signalCount": len(matched_signals),
                "articleCount": len(event_articles),
                "sourceCount": len(event_sources),
            },
        )
        return state

    return handler


def _normalize_news(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        normalized_articles = repository.get_normalized_event_articles(state["event"].id)
        payload = {"articles": list(normalized_articles)}
        state["normalized_articles"] = normalized_articles
        state["payloads"]["normalize_news"] = payload
        _append_step(state, "normalize_news", payload)
        return state

    return handler


def _verify_sources(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        diagnostics = repository.get_event_source_diagnostics(state["event"].id)
        state["source_validation"] = diagnostics
        state["warnings"].extend(str(item) for item in diagnostics["warnings"])
        state["payloads"]["verify_sources"] = diagnostics
        _append_step(state, "verify_sources", diagnostics)
        return state

    return handler


def _link_assets(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload = {
            "relations": list(repository.get_event_asset_relations(state["event"].id)),
            "requestedAssetIds": list(state["asset_ids"]),
        }
        state["payloads"]["link_assets"] = payload
        _append_step(state, "link_assets", payload)
        return state

    return handler


def _fetch_market_snapshots():
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload = {
            "snapshotIds": [snapshot.id for snapshot in state["market_snapshots"]],
            "assetIds": [snapshot.asset_id for snapshot in state["market_snapshots"]],
        }
        state["payloads"]["fetch_market_snapshots"] = payload
        _append_step(state, "fetch_market_snapshots", payload)
        return state

    return handler


def _calculate_reactions(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload: dict[str, Any] = {}
        runtime_signals = []
        for signal in state["matched_signals"]:
            runtime_signal = repository.build_runtime_signal(signal.id)
            runtime_signals.append(runtime_signal)
            payload[runtime_signal.id] = (
                runtime_signal.price_reaction.model_dump(mode="json", by_alias=True)
                if runtime_signal.price_reaction is not None
                else {}
            )
        state["matched_signals"] = tuple(runtime_signals)
        state["payloads"]["calculate_reactions"] = payload
        _append_step(state, "calculate_reactions", payload)
        return state

    return handler


def _analyst_agent(llm_adapter: LLMAdapter):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        outputs = {
            signal.id: llm_adapter.analyze_signal(signal)
            for signal in state["matched_signals"]
        }
        payload = {
            signal_id: {
                "thesis": output.thesis,
                "assumptions": output.assumptions,
                "invalidationConditions": output.invalidation_conditions,
                "suggestedResearchActions": output.suggested_research_actions,
            }
            for signal_id, output in outputs.items()
        }
        state["analyst_outputs"] = outputs
        state["payloads"]["analyst_agent"] = payload
        _append_step(state, "analyst_agent", payload)
        return state

    return handler


def _validate_evidence(repository: FixtureRepository):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload = {}
        validated_signals: list[Signal] = []
        for signal in state["matched_signals"]:
            evidence = repository.get_signal_evidence(signal.id)
            is_complete = repository._signal_evidence_is_complete(signal, evidence)
            if not is_complete:
                signal = signal.model_copy(
                    update={
                        "impact": Impact.UNCERTAIN,
                        "analysis_status": AnalysisStatus.INSUFFICIENT_EVIDENCE,
                        "confidence": min(signal.confidence, 0.59),
                    }
                )
            payload[signal.id] = {
                "evidenceCount": len(evidence),
                "counterEvidenceCount": len([item for item in evidence if not item.supports_signal]),
                "isComplete": is_complete,
            }
            validated_signals.append(signal)
        state["matched_signals"] = tuple(validated_signals)
        state["evidence_checked"] = True
        state["payloads"]["validate_evidence"] = payload
        _append_step(state, "validate_evidence", payload)
        return state

    return handler


def _abstention_guard():
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        advisor_signals = tuple(
            signal
            for signal in state["matched_signals"]
            if signal.analysis_status == AnalysisStatus.COMPLETED
        )
        payload = {
            "uncertainSignals": [
                signal.id
                for signal in state["matched_signals"]
                if signal.analysis_status != AnalysisStatus.COMPLETED
            ],
            "completedSignals": [signal.id for signal in advisor_signals],
        }
        state["warnings"].extend(
            f"Signal {signal_id} requires abstention or revision humana."
            for signal_id in payload["uncertainSignals"]
        )
        state["advisor_signals"] = advisor_signals
        state["payloads"]["abstention_guard"] = payload
        _append_step(state, "abstention_guard", payload)
        return state

    return handler


def _advisor_agent(llm_adapter: LLMAdapter):
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        summary = llm_adapter.build_briefing(
            state.get("advisor_signals", ()),
            warnings=tuple(state.get("warnings", [])),
        )
        payload = {"executiveSummary": summary.executive_summary}
        state["advisor_summary"] = summary
        state["payloads"]["advisor_agent"] = payload
        _append_step(state, "advisor_agent", payload)
        return state

    return handler


def _risk_language_guard():
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        guarded_summary, violations = sanitize_risk_language(
            state.get("advisor_summary").executive_summary
        )
        analyst_payload: dict[str, Any] = {}
        analyst_outputs = state.get("analyst_outputs", {})
        sanitized_outputs = {}
        for signal_id, output in analyst_outputs.items():
            safe_summary, summary_violations = sanitize_risk_language(output.analyst_summary)
            analyst_payload[signal_id] = {"violations": list(summary_violations)}
            sanitized_outputs[signal_id] = output.model_copy(update={"analyst_summary": safe_summary})
        state["analyst_outputs"] = sanitized_outputs
        state["advisor_summary"] = state["advisor_summary"].model_copy(
            update={"executive_summary": guarded_summary}
        )
        if violations:
            state["warnings"].append("RISK_LANGUAGE_BLOCKED")
        payload = {"summaryViolations": list(violations), "analystViolations": analyst_payload}
        state["payloads"]["risk_language_guard"] = payload
        _append_step(state, "risk_language_guard", payload)
        return state

    return handler


def _briefing_builder():
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        payload = {
            "executiveSummary": state["advisor_summary"].executive_summary,
            "eligibleSignalIds": [signal.id for signal in state.get("advisor_signals", ())],
            "warnings": state.get("warnings", []),
        }
        state["payloads"]["briefing_builder"] = payload
        _append_step(state, "briefing_builder", payload)
        return state

    return handler


def _audit_writer():
    def handler(state: MarketAnalysisState) -> MarketAnalysisState:
        completed_signals = len(state.get("advisor_signals", ()))
        terminal_status = (
            AnalysisStatus.COMPLETED.value if completed_signals else AnalysisStatus.INSUFFICIENT_EVIDENCE.value
        )
        payload = {
            "runId": state["run_id"],
            "finalNode": "pending_review",
            "terminalStatus": terminal_status,
            "stepCount": len(state["steps"]) + 1,
            "warnings": state.get("warnings", []),
        }
        state["payloads"]["audit_writer"] = payload
        _append_step(state, "audit_writer", payload)
        return state

    return handler


def _append_step(state: MarketAnalysisState, node: str, payload: dict[str, Any]) -> None:
    sequence = len(state["steps"]) + 1
    timestamp = _step_timestamp(state["run_started_at"], sequence)
    with allow_internal_field_names():
        step = AgentRunStep(
            id=f"step_{state['run_id']}_{sequence:03d}",
            run_id=state["run_id"],
            node=node,
            status="completed",
            timestamp=timestamp,
            payload=payload,
        )
    state["steps"].append(step)
    state["current_node"] = node
    step_sink = state.get("step_sink")
    if step_sink is not None:
        step_sink(step)
        sleep(0.01)


def _step_timestamp(run_started_at: str, sequence: int) -> datetime:
    return datetime.fromisoformat(run_started_at) + timedelta(seconds=sequence)
