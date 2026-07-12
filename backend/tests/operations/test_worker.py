from __future__ import annotations

from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.config import get_market_provider_config
from app.operations.store import InMemoryOperationStore
from app.operations.worker import run_operations_worker
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService
from app.services.provider_runtime_service import build_in_memory_provider_runtime

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_operations_worker_emits_fixture_metrics() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    runtime = build_in_memory_provider_runtime(request_budget=8)
    market_service = MarketDataRuntimeService(
        get_market_provider_config(),
        fixture_provider,
        provider_runtime=runtime,
    )

    report = run_operations_worker(
        task="all",
        market_service=market_service,
        fixture_provider=fixture_provider,
        provider_runtime=runtime,
    )

    assert report.ok is True
    assert report.effective_data_mode == "fixture"
    assert any(metric.name == "nexomercado_worker_events_seen" for metric in report.metrics)
    assert "nexomercado_provider_probe_ok" in report.to_prometheus()


def test_operations_worker_reports_provider_alerts_in_hybrid_mode(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MARKET_DATA_MODE", "hybrid")
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    runtime = build_in_memory_provider_runtime(request_budget=8)
    market_service = MarketDataRuntimeService(
        get_market_provider_config(),
        fixture_provider,
        provider_runtime=runtime,
    )

    report = run_operations_worker(
        task="ingest",
        market_service=market_service,
        fixture_provider=fixture_provider,
        provider_runtime=runtime,
    )

    assert report.ok is True
    assert report.effective_data_mode == "fallback"
    assert any(alert.severity == "warning" for alert in report.alerts)
    assert report.to_json()["task"] == "ingest"


def test_worker_tasks_are_distinct_and_idempotent() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    runtime = build_in_memory_provider_runtime(request_budget=8)
    market_service = MarketDataRuntimeService(
        get_market_provider_config(), fixture_provider, provider_runtime=runtime
    )
    store = InMemoryOperationStore()

    first = run_operations_worker(
        task="ingest", market_service=market_service, fixture_provider=fixture_provider, store=store
    )
    second = run_operations_worker(
        task="ingest", market_service=market_service, fixture_provider=fixture_provider, store=store
    )
    reconcile = run_operations_worker(
        task="reconcile",
        market_service=market_service,
        fixture_provider=fixture_provider,
        store=store,
    )

    assert any(m.name == "nexomercado_worker_rows_written" and m.value > 0 for m in first.metrics)
    assert any(m.name == "nexomercado_worker_rows_written" and m.value == 0 for m in second.metrics)
    assert "event_articles" in store.records
    assert reconcile.effective_data_mode == "fixture"


def test_worker_emits_open_telemetry_spans_and_escapes_labels() -> None:
    fixture_provider = FixtureProvider(REPO_ROOT / "data/fixtures/v1/phase0_bundle.json")
    market_service = MarketDataRuntimeService(get_market_provider_config(), fixture_provider)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    report = run_operations_worker(
        task="cleanup",
        market_service=market_service,
        fixture_provider=fixture_provider,
        tracer=provider.get_tracer("test.operations"),
    )

    span_names = {span.name for span in exporter.get_finished_spans()}
    assert {"nexomercado.worker", "nexomercado.worker.cleanup"} <= span_names
    assert report.metrics[0].__class__("metric", 1, {"label": 'a"b\\c'}).as_prometheus() == (
        'metric{label="a\\"b\\\\c"} 1'
    )
