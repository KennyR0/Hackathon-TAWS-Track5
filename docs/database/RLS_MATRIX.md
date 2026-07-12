# RLS Matrix — NexoMercado AI

## Principio

- **GRANT**: qué operación puede intentar un rol.
- **RLS**: qué filas puede ver o modificar.
- **service_role**: backend FastAPI (bypass RLS); no exponer al frontend.

## Matriz rol × operación

| Entidad | Analyst | Senior analyst | Advisor | Admin |
|---------|---------|----------------|---------|-------|
| Radar/eventos | Leer | Leer | Leer | Leer |
| Señales | Leer | Leer | Leer | Leer |
| Evidencia | Leer | Leer | Leer | Leer |
| Crear revisión | Sí | Sí | Sí | Sí |
| Briefing draft | Sí | Sí | Sí | Sí |
| Briefing shareable | No | Sí | Sí | Sí |
| Auditoría | No | No | No | Leer |
| Gestionar usuarios | No | No | No | Sí |

## Clasificación de tablas

### Grupo A — `organization_id` directo

Política base: `organization_id = private.current_organization_id()`

- organizations, app_users, watchlists, events, agent_runs, briefings, conversations, audit_events

### Grupo B — heredado vía EXISTS

- signals, claims, evidence, signal_reviews, briefing_signals, agent_run_steps, conversation_messages, links

### Grupo C — catálogos

- assets, sources: lectura autenticada
- articles, raw_source_snapshots: lectura si vinculados a eventos accesibles
- market_snapshots, market_observations: lectura autenticada

### Grupo D — interno backend-only

Sin grants para `anon`/`authenticated`:

- provider_cache, provider_budgets, provider_health
- idempotency_keys, audit_events (escritura)
- checkpoints LangGraph, institutional_datasets

## Funciones de autorización (`private`)

- `current_app_user_id()` — mapea `auth.uid()` → `app_users.id`
- `current_organization_id()` — organización del usuario activo
- `current_app_role()` — rol desde `app_users`, no desde JWT metadata
