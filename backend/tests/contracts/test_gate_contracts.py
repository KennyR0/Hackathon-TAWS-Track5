from __future__ import annotations

import json

import pytest
from openapi_spec_validator import validate
from pydantic import ValidationError

from app.contracts.api import AnalysisRequest, build_openapi_document
from app.contracts.entities import AssetRelation, Freshness, PriceReaction


def test_openapi_document_passes_the_openapi_31_validator() -> None:
    validate(build_openapi_document())


def test_snake_case_is_rejected_on_the_json_wire() -> None:
    payload = json.dumps({"event_id": "evt_001", "asset_ids": ["ast_aapl"]})
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate_json(payload)


def test_canonical_json_arrays_and_datetimes_validate() -> None:
    payload = json.dumps({"eventId": "evt_001", "assetIds": ["ast_aapl"]})
    request = AnalysisRequest.model_validate_json(payload)
    assert request.asset_ids == ("ast_aapl",)


@pytest.mark.parametrize(
    ("model", "payload"),
    (
        (PriceReaction, {"assetReturn": "0.1"}),
        (
            AssetRelation,
            {
                "assetId": "ast_aapl",
                "symbol": "AAPL",
                "relationship": "direct",
                "reason": "Coincidencia del emisor.",
                "entityMatchScore": "0.98",
            },
        ),
    ),
)
def test_numeric_strings_are_not_coerced(model: type, payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Freshness.model_validate(
            {
                "evaluatedAt": "2026-07-11T13:00:00",
                "staleAfterSeconds": 3600,
                "isStale": False,
            }
        )


def test_scores_outside_the_unit_interval_are_rejected() -> None:
    with pytest.raises(ValidationError):
        AssetRelation.model_validate(
            {
                "assetId": "ast_aapl",
                "symbol": "AAPL",
                "relationship": "direct",
                "reason": "Coincidencia del emisor.",
                "entityMatchScore": 1.01,
            }
        )
