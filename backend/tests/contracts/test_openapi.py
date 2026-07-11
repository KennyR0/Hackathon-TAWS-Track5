from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator, Mapping
from typing import Any

from conftest import BACKEND_ROOT, OPENAPI_SNAPSHOT

from app.contracts.api import PUBLIC_API_MODELS, build_openapi_document

EXPECTED_OPERATIONS = {
    ("/health", "get"),
    ("/api/v1/events", "get"),
    ("/api/v1/events/{eventId}", "get"),
    ("/api/v1/analyses", "post"),
    ("/api/v1/analyses/{runId}", "get"),
    ("/api/v1/analyses/{runId}/stream", "get"),
    ("/api/v1/signals", "get"),
    ("/api/v1/signals/{signalId}", "get"),
    ("/api/v1/signals/{signalId}/evidence", "get"),
    ("/api/v1/signals/{signalId}/reviews", "get"),
    ("/api/v1/signals/{signalId}/reviews", "post"),
    ("/api/v1/briefings", "post"),
    ("/api/v1/briefings/{briefingId}", "get"),
    ("/api/v1/watchlists/demo-global", "get"),
    ("/api/v1/runs/{runId}/steps", "get"),
}

IDEMPOTENT_OPERATIONS = {
    ("/api/v1/analyses", "post"),
    ("/api/v1/signals/{signalId}/reviews", "post"),
    ("/api/v1/briefings", "post"),
}

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def _canonical_openapi_bytes(document: Mapping[str, Any]) -> bytes:
    rendered = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return rendered.encode("utf-8")


def _operations(document: Mapping[str, Any]) -> Iterator[tuple[str, str, Mapping[str, Any]]]:
    for path, path_item in document["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


def _walk_refs(value: object, location: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key == "$ref" and isinstance(child, str):
                yield child_location, child
            else:
                yield from _walk_refs(child, child_location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_refs(child, f"{location}[{index}]")


def _resolve_json_pointer(document: Mapping[str, Any], reference: str) -> object:
    assert reference.startswith("#/"), f"Only local references are allowed: {reference}"
    current: object = document
    for raw_token in reference[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        assert isinstance(current, dict), f"Reference traverses a non-object: {reference}"
        assert token in current, f"Dangling reference: {reference}"
        current = current[token]
    return current


def _render_in_subprocess(hash_seed: str) -> bytes:
    code = (
        "import json; "
        "from app.contracts.api import build_openapi_document; "
        "print(json.dumps(build_openapi_document(), ensure_ascii=False, "
        "indent=2, sort_keys=True))"
    )
    environment = os.environ.copy()
    environment.update({"PYTHONHASHSEED": hash_seed, "PYTHONUTF8": "1"})
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        env=environment,
        check=True,
        capture_output=True,
    )
    return completed.stdout.replace(b"\r\n", b"\n")


def test_openapi_generation_is_byte_deterministic() -> None:
    first = _canonical_openapi_bytes(build_openapi_document())
    second = _canonical_openapi_bytes(build_openapi_document())
    assert first == second


def test_openapi_is_independent_of_hash_seed() -> None:
    assert _render_in_subprocess("1") == _render_in_subprocess("987654")


def test_committed_openapi_matches_generated_document(openapi_document: dict[str, object]) -> None:
    assert OPENAPI_SNAPSHOT.read_bytes() == _canonical_openapi_bytes(openapi_document)


def test_openapi_contains_all_public_schemas(openapi_document: dict[str, object]) -> None:
    schemas = openapi_document["components"]["schemas"]
    missing = sorted(model.__name__ for model in PUBLIC_API_MODELS if model.__name__ not in schemas)
    assert not missing, f"Public models absent from OpenAPI: {missing}"


def test_openapi_exposes_exact_approved_routes(openapi_document: dict[str, object]) -> None:
    actual = {(path, method) for path, method, _ in _operations(openapi_document)}
    assert actual == EXPECTED_OPERATIONS


def test_openapi_operation_ids_are_unique(openapi_document: dict[str, object]) -> None:
    operation_ids = [operation["operationId"] for _, _, operation in _operations(openapi_document)]
    assert len(operation_ids) == len(set(operation_ids))


def test_idempotency_key_is_required_on_exact_mutating_operations(
    openapi_document: dict[str, object],
) -> None:
    operations_with_header: set[tuple[str, str]] = set()
    for path, method, operation in _operations(openapi_document):
        matching_headers = [
            parameter
            for parameter in operation.get("parameters", [])
            if parameter.get("in") == "header" and parameter.get("name") == "Idempotency-Key"
        ]
        if not matching_headers:
            continue
        operations_with_header.add((path, method))
        assert len(matching_headers) == 1
        header = matching_headers[0]
        assert header["required"] is True
        assert header["schema"]["type"] == "string"
        assert header["schema"]["minLength"] >= 8
        assert header["schema"]["maxLength"] <= 128

    assert operations_with_header == IDEMPOTENT_OPERATIONS


def test_openapi_has_no_dangling_refs(openapi_document: dict[str, object]) -> None:
    references = list(_walk_refs(openapi_document))
    assert references, "OpenAPI unexpectedly contains no references"
    for location, reference in references:
        assert reference.startswith("#/components/schemas/"), (
            f"Unexpected reference target at {location}: {reference}"
        )
        _resolve_json_pointer(openapi_document, reference)


def test_openapi_object_schemas_forbid_additional_properties(
    openapi_document: dict[str, object],
) -> None:
    schemas = openapi_document["components"]["schemas"]
    object_schemas = {
        name: schema
        for name, schema in schemas.items()
        if schema.get("type") == "object" or "properties" in schema
    }
    assert object_schemas
    violations = sorted(
        name
        for name, schema in object_schemas.items()
        if schema.get("additionalProperties") is not False
    )
    assert not violations, f"Object schemas allowing undeclared fields: {violations}"
