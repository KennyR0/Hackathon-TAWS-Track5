# Fase 0 — Matriz de aceptación

Este documento define el gate verificable de la Fase 0. Pydantic es la fuente de verdad; OpenAPI y los fixtures son artefactos derivados o validados contra esos contratos. El gate debe ejecutarse completamente offline.

## Resultado del gate

La Fase 0 solo puede quedar `lista_para_revision` cuando:

1. todos los criterios bloqueantes de esta matriz están aprobados;
2. todos los comandos previstos terminan con código `0`;
3. no existen pruebas omitidas, `xfail` inesperados ni acceso a red;
4. la regeneración de OpenAPI y la validación de fixtures no producen diferencias pendientes;
5. ningún consumidor usa campos fuera de `contracts/consumer-fields.json`.

El cumplimiento técnico no cambia la fase a `aceptada`; esa decisión sigue reservada al usuario.

## Comandos previstos

| ID | Comando | Propósito |
|---|---|---|
| G1 | `python -m pytest -q backend/tests --disable-socket` | Ejecutar contratos, OpenAPI, fixtures, referencias y proyecciones de consumidor sin red. |
| G2 | `python backend/scripts/export_openapi.py --check` | Comprobar que el OpenAPI versionado coincide byte a byte con el generado. |
| G3 | `python backend/scripts/validate_fixtures.py` | Validar el catálogo, el manifiesto SHA-256 y el grafo completo de referencias. |
| G4 | `python backend/scripts/generate_fixtures.py --check` | Comprobar que el bundle versionado coincide byte a byte con el generado. |

Los comandos se ejecutan desde la raíz del repositorio dentro del entorno declarado por `backend/pyproject.toml`.

## Matriz bloqueante

| ID | Criterio de aceptación | Pruebas previstas | Comando |
|---|---|---|---|
| F0-C01 | Existen los enums `Impact`, `AnalysisStatus`, `ReviewStatus`, `BriefingStatus`, `DataMode`, `InstrumentType` y `SourceTier` con exactamente los valores aprobados. Existen los contratos públicos `Source`, `Article`, `Event`, `Asset`, `MarketSnapshot`, `Claim`, `Evidence`, `Signal`, `SignalReview`, `Briefing` y `AgentRun`. | `test_enums_match_approved_wire_values`; `test_all_public_models_validate_canonical_examples`; `test_openapi_contains_all_public_schemas` | G1 |
| F0-C02 | Cada objeto Pydantic público, incluidos los objetos anidados, rechaza campos desconocidos con `extra="forbid"`. No se exponen `Any` ni mapas sin tipo que permitan inventar campos. | `test_all_public_models_forbid_unknown_fields_recursively`; `test_public_models_contain_no_untyped_fields`; `test_openapi_object_schemas_forbid_additional_properties` | G1 |
| F0-C03 | El wire format usa `camelCase` y los nombres canónicos `evidenceIds`, `counterEvidenceIds`, `suggestedResearchActions`, `ReviewRequest.status`, `Article.url` y `Event.eventAt`. Los aliases antiguos o ambiguos son rechazados. | `test_wire_aliases_are_canonical`; `test_legacy_supporting_evidence_ids_is_rejected`; `test_legacy_research_actions_is_rejected`; `test_review_request_uses_status`; `test_consumer_manifest_contains_no_legacy_aliases` | G1 |
| F0-C04 | Los tipos son estrictos. Enums inválidos, IDs vacíos, URLs inválidas, números representados como texto, timestamps sin zona y valores de confianza fuera de `[0, 1]` producen error de validación. El volcado JSON puede validarse otra vez sin cambiar su significado. | `test_public_models_use_strict_types`; `test_confidence_and_scores_are_bounded`; `test_timestamp_fields_require_timezone`; `test_model_dump_round_trip_is_stable` | G1 |
| F0-O01 | OpenAPI se genera sin servidor ni red. Dos generaciones en procesos limpios, con distinto `PYTHONHASHSEED`, producen los mismos bytes UTF-8 con saltos LF y orden canónico. El archivo versionado coincide con esa salida. | `test_openapi_generation_is_byte_deterministic`; `test_openapi_is_independent_of_hash_seed`; `test_committed_openapi_matches_generated_document` | G1, G2 |
| F0-O02 | OpenAPI incluye todos los esquemas públicos, no contiene `$ref` colgantes y conserva required, nullability, enums, aliases y `additionalProperties: false` de Pydantic. | `test_openapi_has_no_dangling_refs`; `test_openapi_required_and_nullable_match_pydantic`; `test_openapi_uses_only_canonical_wire_names` | G1, G2 |
| F0-F01 | El catálogo contiene bundles reproducibles para Apple (`AAPL`, renta variable, benchmark `SPY`), Bitcoin (`BTC`, criptoactivo) y petróleo (commodity con contexto macro). Cada bundle contiene suficientes entidades relacionadas para recorrer evento, artículos, fuentes, activo, snapshot, claim, evidencia y señal. | `test_fixture_catalog_contains_apple_bitcoin_and_oil`; `test_every_fixture_document_validates_with_pydantic`; `test_each_scenario_has_expected_instrument_type`; `test_market_snapshots_cover_related_assets` | G1, G3, G4 |
| F0-F02 | Cada artículo de fixture declara `dataMode="fixture"`, `provider`, `dataAsOf` y `warnings`; no requiere claves, reloj actual ni servicios externos. Los datos de prueba se identifican de forma visible mediante `Source.fixtureOnly`. | `test_fixture_articles_declare_fixture_mode`; `test_fixture_provenance_metadata_is_complete`; `test_fixture_only_sources_are_marked`; `test_contract_suite_requires_no_provider_credentials` | G1, G3 |
| F0-P01 | El catálogo contiene al menos dos publishers originales independientes. La independencia se cuenta por `Source.publisherGroupId` distinto con `isOriginalPublisher=true` e `isAggregator=false`; varios artículos, dominios o filas del mismo grupo cuentan una vez. El proveedor de ingesta no se confunde con el publisher original. | `test_catalog_has_two_independent_original_publishers`; `test_original_publisher_is_distinct_from_ingestion_provider`; `test_same_original_publisher_counts_once`; `test_syndicated_copies_do_not_inflate_publisher_count` | G1, G3 |
| F0-R01 | Los IDs son únicos y no existen referencias huérfanas. Las relaciones `Event→Article`, `Article→Source`, `Signal→Event/Asset/Evidence`, `Claim→Evidence`, `Evidence→Article/Source/Snapshot` y `AgentRun→sourceSnapshotIds` resuelven dentro del catálogo y no cruzan escenarios accidentalmente. | `test_all_fixture_ids_are_unique`; `test_no_fixture_reference_is_orphaned`; `test_evidence_article_and_source_are_consistent`; `test_each_signal_resolves_event_asset_and_snapshot` | G1, G3 |
| F0-R02 | Cada claim puede recorrer `claim → evidence → article/source o marketSnapshot → URL/fecha/hash`. `evidenceIds` y `counterEvidenceIds` existen, pertenecen a la señal y son conjuntos disjuntos. | `test_every_claim_resolves_to_provenance`; `test_signal_evidence_sets_are_disjoint`; `test_signal_evidence_belongs_to_same_scenario` | G1, G3 |
| F0-T01 | Todos los datetimes usan RFC 3339 y se normalizan a UTC `Z`. Se cumple `publishedAt ≤ retrievedAt`, `dataAsOf ≤ retrievedAt`, `createdAt ≤ updatedAt` y `startedAt ≤ finishedAt`. Ninguna fecha supera el `fixtureAsOf` fijo del catálogo. | `test_all_fixture_datetimes_are_utc`; `test_article_published_at_not_after_retrieved_at`; `test_data_as_of_not_after_retrieved_at`; `test_lifecycle_timestamps_are_monotonic`; `test_fixture_timestamps_do_not_exceed_fixture_as_of` | G1, G3 |
| F0-H01 | Los hashes usan `sha256:` seguido de 64 dígitos hexadecimales minúsculos. `contentHash` y los hashes de snapshots se recalculan mediante una canonicalización documentada; el manifiesto del bundle cubre el documento normalizado excluyendo únicamente su propio `fixtureHash` y detecta cualquier alteración. | `test_content_hash_matches_canonical_content`; `test_snapshot_hash_matches_canonical_snapshot`; `test_fixture_manifest_sha256_matches_files`; `test_tampered_fixture_fails_manifest_verification` | G1, G3, G4 |
| F0-U01 | Las rutas requeridas por Radar, Detalle, Briefing y Auditoría están declaradas en `contracts/consumer-fields.json`, existen en OpenAPI y pueden proyectarse desde los fixtures sin aliases alternativos ni campos ad hoc. Las rutas anulables se consumen con manejo explícito de `null`. | `test_consumer_field_manifest_is_valid`; `test_consumer_field_paths_exist_in_openapi`; `test_radar_projection_needs_no_invented_fields`; `test_signal_detail_projection_needs_no_invented_fields`; `test_briefing_projection_needs_no_invented_fields`; `test_audit_projection_needs_no_invented_fields` | G1 |
| F0-N01 | Toda la suite bloquea sockets y no realiza DNS, HTTP ni lectura de credenciales. La carga y serialización de fixtures conserva el resultado con distinto orden de carga y distinto `PYTHONHASHSEED`. | `test_fixture_loader_performs_no_network_io`; `test_openapi_generation_performs_no_network_io`; `test_fixture_load_order_does_not_change_output`; `test_fixture_serialization_is_stable` | G1 |

## Reglas de publishers independientes

- `provider` identifica el mecanismo de ingesta; no demuestra independencia editorial.
- `Source.publisherGroupId` es la clave para contar independencia. Dos marcas del mismo grupo no cuentan como dos publishers.
- `Source.isAggregator=true` impide contar esa fuente como publisher original.
- `Source.fixtureOnly=true` indica datos de demostración, pero no impide representar dos publishers sintéticos independientes.
- El mínimo bloqueante del plan es dos publishers independientes en el catálogo completo. Exigir dos por cada evento es recomendable para la corroboración, pero no será bloqueante sin una actualización explícita del plan.

## Reglas de timestamps y hashes

- Los fixtures usan un `fixtureAsOf` fijo; queda prohibido producir valores mediante `datetime.now()` durante la carga.
- `dataAsOf` es un datetime RFC 3339 con zona y nunca puede ser posterior a `retrievedAt`.
- La canonicalización de `contentHash` debe indicar exactamente qué campos y normalización de texto intervienen.
- El `fixtureHash` se calcula sobre el bundle normalizado con ese único campo sustituido por `null`, evitando autorreferencia.
- Cambiar un byte del contenido cubierto debe cambiar el hash y hacer fallar G3.

## Reglas de campos de consumidor

`contracts/consumer-fields.json` usa rutas con la forma `Schema.field`. `[]` representa cada elemento de una lista. Una ruta listada debe existir en el esquema OpenAPI aunque su valor sea anulable. El frontend no puede introducir un segundo DTO manual con nombres diferentes.

Los nombres heredados `supportingEvidenceIds`, `researchActions`, `newStatus`, `occurredAt`, `Article.sourceUrl`, `mode` y `freshnessWarnings` no son aliases de entrada válidos. `Evidence.sourceUrl` sí conserva su significado aprobado y no se confunde con `Article.url`.

La Auditoría de Fase 0 cubre los campos disponibles de `AgentRun`. El detalle por paso, proveedor, caché y fallback deberá agregarse mediante un contrato explícito posterior, por ejemplo `AgentRunStep`; ningún consumidor puede inventarlo mientras ese contrato no exista.

## Corpus negativo mínimo

Las pruebas deben mutar ejemplos válidos y comprobar que fallan al menos estos casos:

- campo adicional en la raíz y en cada objeto anidado;
- enum desconocido o tipo coercionado;
- alias legado en lugar del nombre canónico;
- timestamp ingenuo, desorden temporal o fecha posterior a `fixtureAsOf`;
- hash mal formado o contenido alterado;
- ID duplicado, referencia huérfana o fuente inconsistente;
- evidencia favorable y contradictoria repetida;
- dos artículos del mismo `publisherGroupId` contados como dos publishers;
- `dataMode` distinto de `fixture` en el catálogo offline;
- ruta de consumidor ausente de OpenAPI o de los fixtures.
