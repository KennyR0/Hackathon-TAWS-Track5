# Database Maintenance — NexoMercado AI

## Funciones (`private` schema)

| Función | Retención / acción |
|---------|-------------------|
| `cleanup_expired_idempotency_keys()` | Elimina filas con `expires_at < now()` |
| `cleanup_expired_provider_cache()` | Elimina caché vencida hace >7 días |
| `reset_provider_budgets()` | Resetea presupuestos cuyo `reset_at` expiró |
| `cleanup_abandoned_checkpoints()` | Limpia checkpoint_writes antiguos (>30 días) |
| `advance_provider_circuit_state()` | `open` → `half_open` cuando `retry_after` vence |

## Ejecución

`pg_cron` no está habilitado en el proyecto MVP. Ejecutar manualmente con `service_role`:

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

## Seguridad

Funciones revocadas a `PUBLIC`; solo `service_role` puede ejecutar.
