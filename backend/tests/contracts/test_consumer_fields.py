from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PathResolution:
    schemas: tuple[Mapping[str, Any], ...]
    nullable: bool


def _schema_from_ref(
    reference: str, component_schemas: Mapping[str, Mapping[str, Any]]
) -> Mapping[str, Any]:
    prefix = "#/components/schemas/"
    if not reference.startswith(prefix):
        raise AssertionError(f"Unsupported external schema reference: {reference}")
    schema_name = reference.removeprefix(prefix)
    if schema_name not in component_schemas:
        raise AssertionError(f"Dangling component schema reference: {reference}")
    return component_schemas[schema_name]


def _non_null_variants(
    schema: Mapping[str, Any], component_schemas: Mapping[str, Mapping[str, Any]]
) -> tuple[list[Mapping[str, Any]], bool]:
    if "$ref" in schema:
        return [_schema_from_ref(schema["$ref"], component_schemas)], False

    for union_key in ("anyOf", "oneOf"):
        if union_key not in schema:
            continue
        variants: list[Mapping[str, Any]] = []
        nullable = False
        for candidate in schema[union_key]:
            if candidate.get("type") == "null":
                nullable = True
                continue
            expanded, candidate_nullable = _non_null_variants(candidate, component_schemas)
            variants.extend(expanded)
            nullable = nullable or candidate_nullable
        return variants, nullable

    return [schema], schema.get("type") == "null"


def resolve_schema_path(
    wire_path: str, component_schemas: Mapping[str, Mapping[str, Any]]
) -> PathResolution:
    parts = wire_path.split(".")
    schema_name, field_parts = parts[0], parts[1:]
    if not field_parts or schema_name not in component_schemas:
        raise AssertionError(f"Unknown schema path root: {wire_path}")

    candidates: list[Mapping[str, Any]] = [component_schemas[schema_name]]
    nullable = False
    for raw_part in field_parts:
        is_array = raw_part.endswith("[]")
        field_name = raw_part[:-2] if is_array else raw_part

        object_candidates: list[Mapping[str, Any]] = []
        for candidate in candidates:
            expanded, candidate_nullable = _non_null_variants(candidate, component_schemas)
            object_candidates.extend(expanded)
            nullable = nullable or candidate_nullable

        field_candidates = [
            candidate["properties"][field_name]
            for candidate in object_candidates
            if field_name in candidate.get("properties", {})
        ]
        if not field_candidates:
            raise AssertionError(f"Missing field at schema path: {wire_path}")

        if not is_array:
            candidates = field_candidates
            continue

        item_candidates: list[Mapping[str, Any]] = []
        for field_schema in field_candidates:
            expanded, field_nullable = _non_null_variants(field_schema, component_schemas)
            nullable = nullable or field_nullable
            for array_schema in expanded:
                if array_schema.get("type") == "array" and "items" in array_schema:
                    item_candidates.append(array_schema["items"])
        if not item_candidates:
            raise AssertionError(f"Expected array at schema path: {wire_path}")
        candidates = item_candidates

    resolved: list[Mapping[str, Any]] = []
    for candidate in candidates:
        expanded, candidate_nullable = _non_null_variants(candidate, component_schemas)
        resolved.extend(expanded)
        nullable = nullable or candidate_nullable
    return PathResolution(tuple(resolved), nullable)


def _assert_consumer_paths(
    consumer_name: str,
    consumer_manifest: dict[str, object],
    openapi_document: dict[str, object],
) -> None:
    schemas = openapi_document["components"]["schemas"]
    paths = consumer_manifest["consumers"][consumer_name]["requiredPaths"]
    failures: list[str] = []
    for path in paths:
        try:
            resolve_schema_path(path, schemas)
        except AssertionError as error:
            failures.append(str(error))
    assert not failures, "\n".join(failures)


def test_consumer_field_manifest_is_valid(consumer_manifest: dict[str, object]) -> None:
    assert consumer_manifest["manifestVersion"] == 1
    assert consumer_manifest["sourceOfTruth"] == "Pydantic -> OpenAPI"
    assert consumer_manifest["wireConvention"] == "camelCase"
    assert set(consumer_manifest["consumers"]) == {
        "radar",
        "signalDetail",
        "briefing",
        "audit",
    }

    for name, consumer in consumer_manifest["consumers"].items():
        required_paths = consumer["requiredPaths"]
        nullable_paths = consumer["nullablePaths"]
        assert required_paths, f"{name} declares no required paths"
        assert len(required_paths) == len(set(required_paths)), f"{name} repeats a required path"
        assert len(nullable_paths) == len(set(nullable_paths)), f"{name} repeats a nullable path"
        assert set(nullable_paths) <= set(required_paths), (
            f"{name} has nullable paths outside requiredPaths"
        )


def test_consumer_nullable_paths_are_nullable_in_openapi(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    schemas = openapi_document["components"]["schemas"]
    violations: list[str] = []
    for consumer_name, consumer in consumer_manifest["consumers"].items():
        for path in consumer["nullablePaths"]:
            resolution = resolve_schema_path(path, schemas)
            if not resolution.nullable:
                violations.append(f"{consumer_name}: {path}")
    assert not violations, f"Paths marked nullable but not nullable in OpenAPI: {violations}"


def test_consumer_canonical_names_exist_in_openapi(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    schemas = openapi_document["components"]["schemas"]
    for path in consumer_manifest["canonicalNames"]:
        resolve_schema_path(path, schemas)


def test_consumer_manifest_contains_no_legacy_aliases(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    schemas = openapi_document["components"]["schemas"]
    all_required_paths = {
        path
        for consumer in consumer_manifest["consumers"].values()
        for path in consumer["requiredPaths"]
    }
    for legacy in consumer_manifest["forbiddenAliases"]:
        schema_name = legacy["schema"]
        alias = legacy["alias"]
        canonical = legacy["use"]
        properties = schemas[schema_name]["properties"]
        assert alias not in properties
        assert canonical in properties
        assert f"{schema_name}.{alias}" not in all_required_paths


def test_radar_projection_needs_no_invented_fields(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    _assert_consumer_paths("radar", consumer_manifest, openapi_document)


def test_signal_detail_projection_needs_no_invented_fields(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    _assert_consumer_paths("signalDetail", consumer_manifest, openapi_document)


def test_briefing_projection_needs_no_invented_fields(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    _assert_consumer_paths("briefing", consumer_manifest, openapi_document)


def test_audit_projection_needs_no_invented_fields(
    consumer_manifest: dict[str, object], openapi_document: dict[str, object]
) -> None:
    _assert_consumer_paths("audit", consumer_manifest, openapi_document)
