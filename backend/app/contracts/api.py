"""API request/response contracts and deterministic OpenAPI generation."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, JsonValue

from .entities import (
    AgentRun,
    AnalysisStatus,
    Article,
    Asset,
    Briefing,
    BriefingStatus,
    Claim,
    ContractModel,
    DataProvenance,
    Event,
    Evidence,
    Identifier,
    MarketSnapshot,
    NonEmptyString,
    Signal,
    SignalReview,
    Source,
)


class HealthResponse(ContractModel):
    status: Literal["ok"]
    service: Literal["nexomercado-api"]
    contract_version: Literal["0.1.0"]


class ApiError(ContractModel):
    code: NonEmptyString
    message: NonEmptyString
    request_id: Identifier | None = None


class AnalysisRequest(ContractModel):
    event_id: Identifier
    asset_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]


class ReviewRequest(ContractModel):
    status: Literal["reviewed", "escalated", "discarded"]
    justification: NonEmptyString


class BriefingRequest(ContractModel):
    watchlist_id: Identifier
    signal_ids: Annotated[tuple[Identifier, ...], Field(min_length=1)]
    status: BriefingStatus


class Watchlist(ContractModel):
    id: Identifier
    name: NonEmptyString
    asset_ids: tuple[Identifier, ...]


class AgentRunStep(ContractModel):
    id: Identifier
    run_id: Identifier
    node: NonEmptyString
    status: Literal["processing", "completed", "failed", "skipped"]
    timestamp: AwareDatetime
    payload: dict[str, JsonValue]


class SseEvent(ContractModel):
    id: Identifier
    run_id: Identifier
    node: NonEmptyString
    status: AnalysisStatus
    timestamp: AwareDatetime
    payload: dict[str, JsonValue]


class EventView(ContractModel):
    event: Event
    articles: Annotated[tuple[Article, ...], Field(min_length=1)]
    sources: Annotated[tuple[Source, ...], Field(min_length=1)]


class EventListResponse(ContractModel):
    data: tuple[EventView, ...]
    meta: DataProvenance


class EventResponse(ContractModel):
    data: EventView
    meta: DataProvenance


class AnalysisResponse(ContractModel):
    data: AgentRun
    meta: DataProvenance


class SignalListResponse(ContractModel):
    data: tuple[Signal, ...]
    meta: DataProvenance


class SignalResponse(ContractModel):
    data: Signal
    meta: DataProvenance


class EvidenceListResponse(ContractModel):
    data: tuple[Evidence, ...]
    meta: DataProvenance


class ReviewListResponse(ContractModel):
    data: tuple[SignalReview, ...]
    meta: DataProvenance


class BriefingResponse(ContractModel):
    data: Briefing
    meta: DataProvenance


class WatchlistResponse(ContractModel):
    data: Watchlist
    meta: DataProvenance


class AgentRunStepsResponse(ContractModel):
    data: tuple[AgentRunStep, ...]
    meta: DataProvenance


PUBLIC_API_MODELS: tuple[type[ContractModel], ...] = (
    Source,
    Article,
    Event,
    Asset,
    MarketSnapshot,
    Claim,
    Evidence,
    Signal,
    SignalReview,
    Briefing,
    AgentRun,
    DataProvenance,
    HealthResponse,
    ApiError,
    AnalysisRequest,
    ReviewRequest,
    BriefingRequest,
    Watchlist,
    AgentRunStep,
    SseEvent,
    EventView,
    EventListResponse,
    EventResponse,
    AnalysisResponse,
    SignalListResponse,
    SignalResponse,
    EvidenceListResponse,
    ReviewListResponse,
    BriefingResponse,
    WatchlistResponse,
    AgentRunStepsResponse,
)


def _schema_ref(model: type[ContractModel]) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{model.__name__}"}


def _json_response(
    model: type[ContractModel], description: str = "Successful response"
) -> dict[str, object]:
    return {
        "description": description,
        "content": {"application/json": {"schema": _schema_ref(model)}},
    }


def _error_responses(*codes: str) -> dict[str, object]:
    return {
        code: _json_response(ApiError, "Request could not be completed") for code in codes
    }


def _path_parameter(name: str) -> dict[str, object]:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "schema": {"type": "string", "minLength": 3},
    }


def _idempotency_header() -> dict[str, object]:
    return {
        "name": "Idempotency-Key",
        "in": "header",
        "required": True,
        "schema": {"type": "string", "minLength": 8, "maxLength": 128},
    }


def _request_body(model: type[ContractModel]) -> dict[str, object]:
    return {
        "required": True,
        "content": {"application/json": {"schema": _schema_ref(model)}},
    }


def _list_filters() -> list[dict[str, object]]:
    return [
        {
            "name": "instrumentType",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
                "enum": ["equity", "etf", "crypto", "commodity", "macro", "credit", "other"],
            },
        },
        {
            "name": "asset",
            "in": "query",
            "required": False,
            "schema": {"type": "string"},
        },
        {
            "name": "publishedAfter",
            "in": "query",
            "required": False,
            "schema": {"type": "string", "format": "date-time"},
        },
    ]


def _merge_model_schemas(models: Iterable[type[ContractModel]]) -> dict[str, object]:
    schemas: dict[str, object] = {}
    for model in models:
        schema = model.model_json_schema(
            by_alias=True,
            mode="serialization",
            ref_template="#/components/schemas/{model}",
        )
        definitions = schema.pop("$defs", {})
        for name, definition in definitions.items():
            existing = schemas.get(name)
            if existing is not None and existing != definition:
                raise ValueError(f"Conflicting JSON Schema definition for {name}")
            schemas[name] = definition
        existing = schemas.get(model.__name__)
        if existing is not None and existing != schema:
            raise ValueError(f"Conflicting public JSON Schema for {model.__name__}")
        schemas[model.__name__] = schema
    return dict(sorted(schemas.items()))


def build_openapi_document() -> dict[str, object]:
    """Build the contract-only OpenAPI document without starting an API runtime."""

    paths: dict[str, object] = {
        "/health": {
            "get": {
                "operationId": "getHealth",
                "summary": "Read service health",
                "responses": {"200": _json_response(HealthResponse)},
            }
        },
        "/api/v1/events": {
            "get": {
                "operationId": "listEvents",
                "summary": "List normalized market events",
                "parameters": _list_filters(),
                "responses": {"200": _json_response(EventListResponse)},
            }
        },
        "/api/v1/events/{eventId}": {
            "get": {
                "operationId": "getEvent",
                "summary": "Read a normalized market event",
                "parameters": [_path_parameter("eventId")],
                "responses": {
                    "200": _json_response(EventResponse),
                    **_error_responses("404"),
                },
            }
        },
        "/api/v1/analyses": {
            "post": {
                "operationId": "createAnalysis",
                "summary": "Start an idempotent market analysis",
                "parameters": [_idempotency_header()],
                "requestBody": _request_body(AnalysisRequest),
                "responses": {
                    "202": _json_response(AnalysisResponse, "Analysis accepted"),
                    **_error_responses("400", "409", "422"),
                },
            }
        },
        "/api/v1/analyses/{runId}": {
            "get": {
                "operationId": "getAnalysis",
                "summary": "Read an analysis run",
                "parameters": [_path_parameter("runId")],
                "responses": {
                    "200": _json_response(AnalysisResponse),
                    **_error_responses("404"),
                },
            }
        },
        "/api/v1/analyses/{runId}/stream": {
            "get": {
                "operationId": "streamAnalysis",
                "summary": "Stream analysis progress with replay support",
                "parameters": [
                    _path_parameter("runId"),
                    {
                        "name": "Last-Event-ID",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Server-Sent Events stream with heartbeat comments",
                        "content": {
                            "text/event-stream": {
                                "schema": {"type": "string"},
                                "x-eventSchema": _schema_ref(SseEvent),
                            }
                        },
                    },
                    **_error_responses("404"),
                },
            }
        },
        "/api/v1/signals": {
            "get": {
                "operationId": "listSignals",
                "summary": "List explainable signals",
                "parameters": _list_filters(),
                "responses": {"200": _json_response(SignalListResponse)},
            }
        },
        "/api/v1/signals/{signalId}": {
            "get": {
                "operationId": "getSignal",
                "summary": "Read an explainable signal",
                "parameters": [_path_parameter("signalId")],
                "responses": {
                    "200": _json_response(SignalResponse),
                    **_error_responses("404"),
                },
            }
        },
        "/api/v1/signals/{signalId}/evidence": {
            "get": {
                "operationId": "listSignalEvidence",
                "summary": "Read supporting and counter evidence",
                "parameters": [_path_parameter("signalId")],
                "responses": {
                    "200": _json_response(EvidenceListResponse),
                    **_error_responses("404"),
                },
            }
        },
        "/api/v1/signals/{signalId}/reviews": {
            "post": {
                "operationId": "createSignalReview",
                "summary": "Record an immutable human review",
                "parameters": [_path_parameter("signalId"), _idempotency_header()],
                "requestBody": _request_body(ReviewRequest),
                "responses": {
                    "201": _json_response(ReviewListResponse, "Review recorded"),
                    **_error_responses("400", "404", "409", "422"),
                },
            },
            "get": {
                "operationId": "listSignalReviews",
                "summary": "List immutable human reviews",
                "parameters": [_path_parameter("signalId")],
                "responses": {
                    "200": _json_response(ReviewListResponse),
                    **_error_responses("404"),
                },
            },
        },
        "/api/v1/briefings": {
            "post": {
                "operationId": "createBriefing",
                "summary": "Create an idempotent deterministic briefing",
                "parameters": [_idempotency_header()],
                "requestBody": _request_body(BriefingRequest),
                "responses": {
                    "201": _json_response(BriefingResponse, "Briefing created"),
                    **_error_responses("400", "409", "422"),
                },
            }
        },
        "/api/v1/briefings/{briefingId}": {
            "get": {
                "operationId": "getBriefing",
                "summary": "Read a briefing",
                "parameters": [_path_parameter("briefingId")],
                "responses": {
                    "200": _json_response(BriefingResponse),
                    **_error_responses("404"),
                },
            }
        },
        "/api/v1/watchlists/demo-global": {
            "get": {
                "operationId": "getDemoWatchlist",
                "summary": "Read the fixed demo watchlist",
                "responses": {"200": _json_response(WatchlistResponse)},
            }
        },
        "/api/v1/runs/{runId}/steps": {
            "get": {
                "operationId": "listAgentRunSteps",
                "summary": "List auditable run steps",
                "parameters": [_path_parameter("runId")],
                "responses": {
                    "200": _json_response(AgentRunStepsResponse),
                    **_error_responses("404"),
                },
            }
        },
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "NexoMercado AI API",
            "version": "0.1.0",
            "description": "Contrato del MVP; la implementación del runtime comienza en Fase 1.",
        },
        "paths": deepcopy(paths),
        "components": {"schemas": _merge_model_schemas(PUBLIC_API_MODELS)},
    }


__all__ = [
    "PUBLIC_API_MODELS",
    "AgentRunStep",
    "AnalysisRequest",
    "AnalysisResponse",
    "ApiError",
    "BriefingRequest",
    "BriefingResponse",
    "EventListResponse",
    "EventResponse",
    "EventView",
    "HealthResponse",
    "ReviewRequest",
    "SseEvent",
    "SignalListResponse",
    "SignalResponse",
    "Watchlist",
    "WatchlistResponse",
    "build_openapi_document",
]
