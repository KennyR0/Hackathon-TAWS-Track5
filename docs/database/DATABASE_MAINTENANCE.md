# Database Maintenance — NexoMercado AI

## Funciones (`private` schema)

| Función | Retención / acción |
|---------|-------------------|
| `cleanup_expired_idempotency_keys()` | Elimina filas con `expires_at < now()` |
| `cleanup_expired_provider_cache()` | Elimina caché vencida hace >7 días |
| `reset_provider_budgets()` | Resetea presupuestos cuyo `reset_at` expiró |
| `cleanup_abandoned_checkpoints()` | Limpia checkpoint_writes antiguos (>30 días) |
| `advance_provider_circuit_state()` | `open` → `half_open` cuando `retry_after` vence |
| `touch_keepalive()` | Inserta un heartbeat y purga filas >7 días en `private.db_keepalive` |

## Keep-alive (plan Free)

Migración: `20260713030117_db_keepalive.sql`

Objetos dedicados (no tocan tablas de dominio):

| Objeto | Rol |
|--------|-----|
| `private.db_keepalive` | Tabla vacía al inicio; acumula 1 fila por ping |
| `private.touch_keepalive()` | Inserta heartbeat y limpia filas antiguas |
| `cron.job` `db-keepalive-12h` | Ejecuta el ping cada 12 h (`0 */12 * * *`, 00:00 y 12:00 UTC) |

**Limitación:** en el plan Free, Supabase puede pausar proyectos tras ~7 días sin actividad suficiente. La documentación oficial enfatiza llamadas a la **API REST**; este heartbeat SQL interno mantiene Postgres activo pero **no garantiza** evitar la pausa. Si el proyecto sigue pausándose, añadir un ping externo (p. ej. `backend/scripts/check_supabase_connection.py` vía Render/GitHub Actions).

Verificación:

```sql
select jobid, jobname, schedule, command from cron.job
where jobname = 'db-keepalive-12h';

select private.touch_keepalive();
select count(*), max(pinged_at) from private.db_keepalive;

select status, start_time, end_time
from cron.job_run_details
order by start_time desc
limit 5;

select pid, application_name, state
from pg_stat_activity
where application_name ilike 'pg_cron%';
```

## Ejecución

`pg_cron` está habilitado para el keep-alive. Las funciones de limpieza siguen disponibles para ejecución manual con `service_role`:

```sql
select private.cleanup_expired_idempotency_keys();
select private.cleanup_expired_provider_cache();
select private.reset_provider_budgets();
select private.cleanup_abandoned_checkpoints();
select private.advance_provider_circuit_state();
```

## Política de retención

| Recurso | Política MVP |
|---------|--------------|
| idempotency_keys | Post `expires_at` |
| provider_cache | +7 días tras vencimiento |
| checkpoints abandonados | 30 días |
| audit_events | Sin purge MVP |
| signal_reviews | Nunca auto-eliminar |
| db_keepalive | 7 días (auto-purge en cada ping) |

## Seguridad

Funciones revocadas a `PUBLIC`; solo `service_role` puede ejecutar.
