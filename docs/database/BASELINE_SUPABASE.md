# Baseline Supabase — NexoMercado AI

Fecha: 2026-07-12  
Proyecto remoto: `Track5 Hackathon` (`oxmvmyyrhfqcambqqfkg`, us-east-1)  
CLI: `supabase` v2.98.2

## Estado de migraciones

| Versión | Nombre | Local | Remoto |
|---------|--------|-------|--------|
| 20260712030933 | remote_schema | Sí | Sí |
| 20260712033000 | phase5_langgraph_checkpoints | Sí (sincronizado B0) | Sí |
| 20260712044313 | phase_4_runtime_persistence | Sí | Sí |
| 20260712050000 | phase5_canonical_demo_global_watchlist | Sí (sincronizado B0) | Sí |

`supabase migration list --linked`: paridad local = remoto (4/4).

## Inventario remoto (31 tablas)

**Dominio:** organizations, app_users, sources, assets, watchlists, watchlist_assets, raw_source_snapshots, articles, events, event_articles, event_asset_relations, market_snapshots, market_observations, agent_runs, agent_run_steps, agent_run_source_snapshots, signals, claims, evidence, evidence_market_snapshots, claim_evidence_links, signal_evidence_links, signal_reviews, briefings, briefing_signals, idempotency_keys, audit_events.

**LangGraph:** checkpoint_migrations, checkpoints, checkpoint_blobs, checkpoint_writes.

**Enums (8):** analysis_status, briefing_status, data_mode, impact_status, instrument_type, review_status, source_tier.

**Funciones públicas (5):** set_updated_at, apply_signal_review, prevent_signal_review_mutation, enforce_shareable_briefing, enforce_shareable_briefing_signal.

**Políticas RLS:** 0 (esperado hasta B5).

**Extensiones:** pgcrypto, pg_stat_statements, uuid-ossp, supabase_vault. pg_cron no habilitado.

## Diferencias detectadas y resueltas en B0

| Diferencia | Estado |
|------------|--------|
| 2 migraciones faltantes en local | Resuelto vía `supabase migration fetch --linked` |
| Backend `audit_events` usaba `event_type`/`payload` | Resuelto: ahora `action`/`metadata`/`actor_user_id` |
| `supabase/schema.sql` incompleto para runtime de proveedores | Actualizado como baseline operativo mínimo; las migraciones remotas siguen siendo la fuente cloud |
| `supabase/` gitignored | Baseline reproducible en este documento |

## Drift `supabase db diff --linked`

Shadow DB falla al aplicar `phase5_canonical_demo_global_watchlist` sin seed de `organizations` — esperado en entorno vacío. **No hay drift destructivo** contra remoto (sin DROP/recreate de tablas existentes).

## Security Advisor (pre-B1)

- 5× `function_search_path_mutable` (WARN) — corregir en B1
- 31× `rls_enabled_no_policy` (INFO) — corregir en B5

## Performance Advisor (pre-B1)

- 4× FK sin índice — corregir en B1
- Índices `unused` — pospuestos (poco tráfico)

## Tests baseline

```
pytest tests/repositories/test_supabase_repository.py tests/contracts/test_supabase_config.py — 12 passed
```

## Riesgos

1. `supabase/` no versionado en git — riesgo de drift entre máquinas; ejecutar checklist B0 en cada entorno.
2. `schema.sql` es baseline operativo mínimo para onboarding; usar migraciones remotas/CLI como fuente canónica cloud.
3. Cambios cloud requieren autorización explícita antes de `supabase db push`.

## Confirmación

**Se puede continuar con B1.** Migraciones alineadas, desalineación `audit_events` corregida, tests verdes.
