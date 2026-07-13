"""Idempotent operations worker with traces, metrics, and actionable alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal

from opentelemetry import trace
from opentelemetry.trace import Tracer

from app.market_universe import MarketUniverse, load_market_universe
from app.operations.store import InMemoryOperationStore, OperationStore
from app.providers.base import ProviderProbeResult
from app.providers.fixture_provider import FixtureProvider
from app.providers.live_market import MarketDataRuntimeService, MarketRuntimeSnapshot
from app.services.provider_runtime_service import ProviderRuntimeBundle

WorkerTask = Literal["ingest", "prices", "macro", "reconcile", "cleanup", "all"]
AtomicTask = Literal["ingest", "prices", "macro", "reconcile", "cleanup"]
AlertSeverity = Literal["info", "warning", "critical"]
TASK_ORDER: tuple[AtomicTask, ...] = ("ingest", "prices", "macro", "reconcile", "cleanup")


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


@dataclass(frozen=True)
class OperationMetric:
    name: str
    value: float
    labels: dict[str, str]

    def as_prometheus(self) -> str:
        label_text = ",".join(
            f'{key}="{_escape_label(value)}"' for key, value in sorted(self.labels.items())
        )
        suffix = f"{{{label_text}}}" if label_text else ""
        return f"{self.name}{suffix} {self.value:g}"


@dataclass(frozen=True)
class OperationAlert:
    severity: AlertSeverity
    code: str
    message: str
    provider: str | None = None


@dataclass(frozen=True)
class OperationReport:
    run_id: str
    task: WorkerTask
    started_at: datetime
    finished_at: datetime
    effective_data_mode: str
    metrics: tuple[OperationMetric, ...]
    alerts: tuple[OperationAlert, ...]

    @property
    def ok(self) -> bool:
        return not any(alert.severity == "critical" for alert in self.alerts)

    @property
    def partial(self) -> bool:
        return self.ok and any(alert.severity == "warning" for alert in self.alerts)

    def to_json(self) -> dict[str, object]:
        return {
            "runId": self.run_id,
            "task": self.task,
            "ok": self.ok,
            "partial": self.partial,
            "startedAt": self.started_at.isoformat(),
            "finishedAt": self.finished_at.isoformat(),
            "effectiveDataMode": self.effective_data_mode,
            "metrics": [
                {"name": item.name, "value": item.value, "labels": item.labels}
                for item in self.metrics
            ],
            "alerts": [item.__dict__ for item in self.alerts],
        }

    def to_prometheus(self) -> str:
        return "\n".join(metric.as_prometheus() for metric in self.metrics)


def run_operations_worker(
    *,
    task: WorkerTask,
    market_service: MarketDataRuntimeService,
    fixture_provider: FixtureProvider,
    provider_runtime: ProviderRuntimeBundle | None = None,
    store: OperationStore | None = None,
    tracer: Tracer | None = None,
) -> OperationReport:
    started_at = datetime.now(UTC)
    started_clock = perf_counter()
    run_id = f"ops_{started_at.strftime('%Y%m%d%H%M%S%f')}_{task}"
    effective_store = store or InMemoryOperationStore()
    tasks = TASK_ORDER if task == "all" else (task,)
    bundle = fixture_provider.load_bundle()
    universe = load_market_universe()
    metrics: list[OperationMetric] = []
    alerts: list[OperationAlert] = []
    effective_mode = "fixture"
    effective_tracer = tracer or trace.get_tracer("nexomercado.operations")
    metrics.append(
        OperationMetric(
            "nexomercado_worker_events_seen",
            float(len(bundle.events)),
            {"task": task, "mode": "fixture"},
        )
    )

    with effective_tracer.start_as_current_span("nexomercado.worker") as run_span:
        run_span.set_attribute("nexomercado.run_id", run_id)
        run_span.set_attribute("nexomercado.task", task)
        for atomic_task in tasks:
            task_started = perf_counter()
            try:
                with effective_tracer.start_as_current_span(
                    f"nexomercado.worker.{atomic_task}"
                ) as span:
                    snapshot = _snapshot_for_task(atomic_task, market_service, universe)
                    if snapshot is not None:
                        effective_mode = snapshot.data_mode
                        alerts.extend(_snapshot_alerts(snapshot))
                        metrics.extend(_provider_metrics(atomic_task, snapshot.checks))
                        metrics.extend(_snapshot_metrics(atomic_task, snapshot))
                    rows_read, rows_written = _execute_task(
                        atomic_task,
                        effective_store,
                        bundle,
                        snapshot,
                        universe,
                    )
                    span.set_attribute("nexomercado.rows_read", rows_read)
                    span.set_attribute("nexomercado.rows_written", rows_written)
                    span.set_attribute("nexomercado.data_mode", effective_mode)
                    metrics.extend(_task_metrics(atomic_task, rows_read, rows_written, True))
            except Exception as exc:
                alerts.append(
                    OperationAlert(
                        severity="critical",
                        code=f"{atomic_task.upper()}_FAILED",
                        message=f"La tarea {atomic_task} fallo: {type(exc).__name__}",
                    )
                )
                metrics.extend(_task_metrics(atomic_task, 0, 0, False))
                trace.get_current_span().record_exception(exc)
            finally:
                metrics.append(
                    OperationMetric(
                        "nexomercado_worker_task_duration_seconds",
                        perf_counter() - task_started,
                        {"task": atomic_task},
                    )
                )

        if provider_runtime is not None:
            metrics.extend(_runtime_metrics(task, provider_runtime))
        run_span.set_attribute("nexomercado.ok", not any(a.severity == "critical" for a in alerts))

    metrics.append(
        OperationMetric(
            "nexomercado_worker_run_duration_seconds",
            perf_counter() - started_clock,
            {"task": task, "mode": effective_mode},
        )
    )
    return OperationReport(
        run_id=run_id,
        task=task,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        effective_data_mode=effective_mode,
        metrics=tuple(metrics),
        alerts=tuple(alerts),
    )


def _snapshot_for_task(
    task: AtomicTask,
    market_service: MarketDataRuntimeService,
    universe: MarketUniverse,
) -> MarketRuntimeSnapshot | None:
    if task == "ingest":
        return market_service.collect_demo_snapshot()
    if task == "prices":
        instruments = tuple(item for item in universe.instruments if item.series_id is None)
        return market_service.collect_universe_snapshot(instruments)
    if task == "macro":
        instruments = tuple(item for item in universe.instruments if item.series_id is not None)
        return market_service.collect_universe_snapshot(instruments)
    return None


def _execute_task(
    task: AtomicTask,
    store: OperationStore,
    bundle,
    snapshot: MarketRuntimeSnapshot | None,
    universe: MarketUniverse,
) -> tuple[int, int]:
    if task == "ingest":
        if snapshot is not None:
            live_result = store.ingest_runtime(snapshot, universe)
            if live_result[0] > 0:
                return live_result
        return store.ingest(bundle)
    if task == "prices":
        return store.market_runtime(snapshot, universe) if snapshot is not None else (0, 0)
    if task == "macro":
        return store.market_runtime(snapshot, universe) if snapshot is not None else (0, 0)
    if task == "reconcile":
        return store.reconcile(bundle)
    return store.cleanup(datetime.now(UTC))


def _snapshot_alerts(snapshot: MarketRuntimeSnapshot) -> tuple[OperationAlert, ...]:
    return tuple(
        OperationAlert(
            severity="info" if snapshot.data_mode == "fixture" else "warning",
            code=warning,
            message=(
                "Modo fixture activo; no se consultaron proveedores externos."
                if snapshot.data_mode == "fixture"
                else "Proveedor degradado; se conserva fallback auditable."
            ),
            provider=snapshot.provider,
        )
        for warning in snapshot.warnings
    )


def _task_metrics(task: AtomicTask, rows_read: int, rows_written: int, ok: bool):
    labels = {"task": task}
    return (
        OperationMetric("nexomercado_worker_task_ok", 1.0 if ok else 0.0, labels),
        OperationMetric("nexomercado_worker_rows_read", float(rows_read), labels),
        OperationMetric("nexomercado_worker_rows_written", float(rows_written), labels),
    )


def _snapshot_metrics(task: AtomicTask, snapshot: MarketRuntimeSnapshot):
    labels = {"task": task, "mode": snapshot.data_mode}
    return (
        OperationMetric("nexomercado_worker_requests_used", float(snapshot.requests_used), labels),
        OperationMetric(
            "nexomercado_worker_request_budget",
            float(snapshot.request_budget),
            labels,
        ),
        OperationMetric(
            "nexomercado_worker_fallback_active",
            1.0 if snapshot.data_mode == "fallback" else 0.0,
            labels,
        ),
    )


def _provider_metrics(task: str, checks: dict[str, ProviderProbeResult]):
    return tuple(
        OperationMetric(
            "nexomercado_provider_probe_ok",
            1.0 if value.ok else 0.0,
            {"task": task, "provider": value.provider, "check": key, "mode": value.data_mode},
        )
        for key, value in checks.items()
    )


def _runtime_metrics(task: str, provider_runtime: ProviderRuntimeBundle):
    providers = ("gdelt", "finnhub", "twelve_data", "coingecko", "fred")
    return tuple(
        OperationMetric(
            "nexomercado_provider_circuit_open",
            1.0 if provider_runtime.health.is_circuit_open(provider) else 0.0,
            {"task": task, "provider": provider},
        )
        for provider in providers
    )
