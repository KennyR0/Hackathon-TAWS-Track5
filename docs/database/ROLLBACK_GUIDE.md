# Rollback Guide — NexoMercado AI Database

## Principio

No modificar migraciones históricas ya aplicadas. Rollback = nueva migración compensatoria o restore de backup.

## Orden de migraciones (remoto)

1. `20260712030933` remote_schema
2. `20260712033000` phase5_langgraph_checkpoints
3. `20260712044313` phase_4_runtime_persistence
4. `20260712050000` phase5_canonical_demo_global_watchlist
5. `20260712175320` harden_database_functions
6. `20260712175321` add_missing_foreign_key_indexes
7. `20260712175709` add_provider_runtime_tables
8. `20260712175928` add_conversations
9. `20260712175929` link_app_users_to_auth
10. `20260712175942` add_authorization_helpers
11. `20260712180020` add_rls_policies_and_grants
12. `20260712180029` add_institutional_datasets
13. `20260712180041` add_database_maintenance_jobs

## Rollback por bloque

| Bloque | Acción compensatoria |
|--------|---------------------|
| B1 hardening | Restaurar funciones sin `search_path` (no recomendado) |
| B2 providers | `drop table provider_*` |
| B3 conversations | `drop table conversation_messages, conversations`; drop FK en agent_runs |
| B4 auth | `drop column auth_user_id`; `drop schema private cascade` |
| B5 RLS | `drop policy` por tabla; `revoke` grants |
| B6 datasets | `drop table institutional_datasets`; drop funciones maintenance |

## Backup recomendado

Antes de aplicar en producción:

```bash
supabase db dump --linked -f backup_pre_finalization.sql
```

## Reproducir localmente

```bash
supabase migration list --linked
supabase migration fetch --linked --yes
```

Ver [BASELINE_SUPABASE.md](BASELINE_SUPABASE.md).
