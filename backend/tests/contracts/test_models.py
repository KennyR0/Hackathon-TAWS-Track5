from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.api import PUBLIC_API_MODELS, ReviewRequest
from app.contracts.entities import (
    AnalysisStatus,
    Article,
    BriefingStatus,
    ContractModel,
    DataMode,
    Event,
    Impact,
    InstrumentType,
    ReviewStatus,
    Signal,
    SourceTier,
)

EXPECTED_ENUM_VALUES = (
    (Impact, ("positive", "negative", "neutral", "uncertain")),
    (
        AnalysisStatus,
        ("processing", "completed", "insufficient_evidence", "failed"),
    ),
    (ReviewStatus, ("pending_review", "reviewed", "escalated", "discarded")),
    (BriefingStatus, ("draft", "shareable")),
    (DataMode, ("fixture", "live", "fallback")),
    (
        InstrumentType,
        ("equity", "etf", "crypto", "commodity", "macro", "credit", "other"),
    ),
    (SourceTier, ("A", "B", "C", "D")),
)

LEGACY_ALIASES = (
    (Signal, "supportingEvidenceIds", "evidenceIds"),
    (Signal, "researchActions", "suggestedResearchActions"),
    (ReviewRequest, "newStatus", "status"),
    (Event, "occurredAt", "eventAt"),
    (Article, "sourceUrl", "url"),
    (Article, "mode", "dataMode"),
    (Article, "freshnessWarnings", "warnings"),
)


def _contract_model_descendants() -> tuple[type[ContractModel], ...]:
    descendants: set[type[ContractModel]] = set()
    pending = list(ContractModel.__subclasses__())
    while pending:
        model = pending.pop()
        if model in descendants:
            continue
        descendants.add(model)
        pending.extend(model.__subclasses__())
    return tuple(sorted(descendants, key=lambda model: model.__name__))


def _assert_extra_forbidden(
    error: pytest.ExceptionInfo[ValidationError], expected_location: tuple[str, ...]
) -> None:
    matching_errors = [
        item
        for item in error.value.errors()
        if item["type"] == "extra_forbidden" and item["loc"] == expected_location
    ]
    assert matching_errors, error.value.errors()


@pytest.mark.parametrize(
    ("enum_type", "expected_values"),
    EXPECTED_ENUM_VALUES,
    ids=lambda value: value.__name__ if isinstance(value, type) else None,
)
def test_enums_match_approved_wire_values(
    enum_type: type, expected_values: tuple[str, ...]
) -> None:
    assert tuple(member.value for member in enum_type) == expected_values


def test_all_public_models_forbid_unknown_fields_recursively() -> None:
    models = set(PUBLIC_API_MODELS) | set(_contract_model_descendants())
    violations = sorted(
        model.__name__ for model in models if model.model_config.get("extra") != "forbid"
    )
    assert not violations, f"Models without extra='forbid': {violations}"


@pytest.mark.parametrize("model", PUBLIC_API_MODELS, ids=lambda model: model.__name__)
def test_public_models_reject_unknown_fields(model: type[ContractModel]) -> None:
    with pytest.raises(ValidationError) as error:
        model.model_validate({"unexpectedConsumerField": "not-declared"})
    _assert_extra_forbidden(error, ("unexpectedConsumerField",))


def test_nested_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError) as error:
        Signal.model_validate({"asset": {"unexpectedConsumerField": True}})
    _assert_extra_forbidden(error, ("asset", "unexpectedConsumerField"))


@pytest.mark.parametrize(
    ("model", "legacy_alias", "canonical_alias"),
    LEGACY_ALIASES,
    ids=lambda value: value.__name__ if isinstance(value, type) else str(value),
)
def test_wire_aliases_are_canonical(
    model: type[ContractModel], legacy_alias: str, canonical_alias: str
) -> None:
    properties = model.model_json_schema(
        by_alias=True,
        mode="serialization",
        ref_template="#/components/schemas/{model}",
    )["properties"]
    assert canonical_alias in properties
    assert legacy_alias not in properties

    with pytest.raises(ValidationError) as error:
        model.model_validate({legacy_alias: "legacy-value"})
    _assert_extra_forbidden(error, (legacy_alias,))


def test_legacy_supporting_evidence_ids_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        Signal.model_validate({"supportingEvidenceIds": []})
    _assert_extra_forbidden(error, ("supportingEvidenceIds",))


def test_legacy_research_actions_is_rejected() -> None:
    with pytest.raises(ValidationError) as error:
        Signal.model_validate({"researchActions": []})
    _assert_extra_forbidden(error, ("researchActions",))


def test_review_request_uses_status() -> None:
    request = ReviewRequest.model_validate(
        {"status": "reviewed", "justification": "Validación humana completada."}
    )
    assert request.model_dump(by_alias=True, mode="json") == {
        "status": "reviewed",
        "justification": "Validación humana completada.",
    }

    schema = ReviewRequest.model_json_schema(by_alias=True, mode="serialization")
    assert set(schema["properties"]) == {"status", "justification"}
    assert schema["properties"]["status"]["enum"] == [
        "reviewed",
        "escalated",
        "discarded",
    ]
    assert set(schema["required"]) == {"status", "justification"}


def test_review_request_rejects_new_status() -> None:
    with pytest.raises(ValidationError) as error:
        ReviewRequest.model_validate(
            {"newStatus": "reviewed", "justification": "Alias heredado."}
        )
    _assert_extra_forbidden(error, ("newStatus",))
