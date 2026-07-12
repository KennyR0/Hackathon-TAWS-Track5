# Final Database Report — NexoMercado AI

Fecha: 2026-07-12  
Proyecto: `oxmvmyyrhfqcambqqfkg` (Track5 Hackathon)

## Resumen

Plan B0–B7 ejecutado. Base remota actualizada con 13 migraciones, nuevas tablas operativas, auth helpers, RLS multi-organización y mantenimiento programable. Backend alineado con esquema remoto (`audit_events`, proveedores, conversaciones, auth).

## Migraciones creadas (bloques B1–B7)

| Migración | Bloque |
|-----------|--------|
| harden_database_functions | B1 |
| add_missing_foreign_key_indexes | B1 |
| add_provider_runtime_tables | B2 |
| add_conversations | B3 |
| link_app_users_to_auth | B4 |
| add_authorization_helpers | B4 |
| add_rls_policies_and_grants | B5 |
| add_institutional_datasets | B6 |
| add_database_maintenance_jobs | B6 |

## Tablas creadas

- `provider_cache`, `provider_budgets`, `provider_health`
- `conversations`, `conversation_messages`
- `institutional_datasets`

## Tablas modificadas

- `app_users`: `auth_user_id`, `is_active`, `updated_at`
- `agent_runs`: FK `conversation_id` → `conversations`

## Funciones modificadas (B1)

- `set_updated_at`, `apply_signal_review`, `prevent_signal_review_mutation`
- `enforce_shareable_briefing`, `enforce_shareable_briefing_signal`
- Todas con `set search_path = ''`

## Funciones nuevas (`private`)

- `current_app_user_id`, `current_organization_id`, `current_app_role`
- `cleanup_expired_idempotency_keys`, `cleanup_expired_provider_cache`
- `reset_provider_budgets`, `cleanup_abandoned_checkpoints`, `advance_provider_circuit_state`

## Políticas RLS

~35 políticas en tablas Grupo A/B/C. Grupo D sin acceso cliente.

## Índices añadidos (B1)

- `audit_events_actor_user_id_idx`, `audit_events_organization_id_idx`
- `briefings_organization_id_idx`, `signals_current_reviewed_by_idx`

## Archivos backend modificados/creados

| Archivo | Cambio |
|---------|--------|
| `repositories/supabase_repository.py` | `audit_events` → `action`/`metadata`/`actor_user_id` |
| `repositories/provider_*_repository.py` | Nuevo (B2) |
| `services/provider_runtime_service.py` | Nuevo (B2) |
| `providers/live_market.py` | Integración caché/budget/circuit durable |
| `api/dependencies.py` | Provider runtime por backend |
| `models/conversations.py` | Nuevo (B3) |
| `repositories/conversation_repository.py` | Nuevo (B3) |
| `services/conversation_service.py` | Nuevo (B3) |
| `security/auth.py`, `permissions.py` | Nuevo (B4) |
| `tests/repositories/test_provider_runtime_repositories.py` | Nuevo |
| `tests/services/test_conversation_service.py` | Nuevo |
| `tests/security/test_auth_permissions.py` | Nuevo |
| `frontend/src/lib/database.types.ts` | Generado |

## Documentación

- [BASELINE_SUPABASE.md](BASELINE_SUPABASE.md)
- [RLS_MATRIX.md](RLS_MATRIX.md)
- [PROVIDER_PERSISTENCE.md](PROVIDER_PERSISTENCE.md)
- [DATABASE_MAINTENANCE.md](DATABASE_MAINTENANCE.md)
- [ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md)

## Tests ejecutados

```bash
pytest tests/repositories/test_supabase_repository.py -q          # 5 passed
pytest tests/repositories/test_provider_runtime_repositories.py -q # 5 passed
pytest tests/services/test_conversation_service.py -q           # 2 passed
pytest tests/security/test_auth_permissions.py -q               # 4 passed
```

SQL: `supabase/tests/database/000_setup.sql` … `060_internal_tables_test.sql`

## Advisors

### Antes (B0)

- 5× `function_search_path_mutable` (WARN)
- 4× FK sin índice (INFO)
- 31× `rls_enabled_no_policy` (INFO)

### Después (B7)

- 0× `function_search_path_mutable`
- 0× FK sin índice (los 4 listados)
- 9× `rls_enabled_no_policy` en tablas internas Grupo D (INFO, esperado)

## Riesgos pendientes

1. `supabase/` gitignored — sincronizar con `migration fetch` en cada entorno.
2. `schema.sql` legacy — no usar para bootstrap.
3. `pg_cron` no habilitado — jobs maintenance manuales.
4. Auth JWT requiere `AUTH_ENABLED=true` y usuario vinculado en `app_users.auth_user_id`.

## Comandos reproducibles

```bash
supabase migration list --linked
supabase migration fetch --linked --yes
supabase gen types typescript --linked > frontend/src/lib/database.types.ts
cd backend && python -m pytest tests/repositories tests/services tests/security -q
```

## Estrategia rollback

Ver [ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md).
