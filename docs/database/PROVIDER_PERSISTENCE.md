# Provider Persistence — NexoMercado AI

## Tablas

| Tabla | Propósito |
|-------|-----------|
| `provider_cache` | Respuestas cacheadas por `(provider, cache_key)` con `expires_at` |
| `provider_budgets` | Cuota por proveedor y período (`minute/hour/day/month`) |
| `provider_health` | Circuit breaker `closed/open/half_open` |

## Backend

| Módulo | Rol |
|--------|-----|
| `provider_cache_repository.py` | get/set caché |
| `provider_budget_repository.py` | consumo transaccional de cuota |
| `provider_health_repository.py` | fallos consecutivos y circuito |
| `provider_runtime_service.py` | bundle in-memory vs Supabase |
| `live_market.py` | integración en `MarketDataRuntimeService._safe_probe` |

## Modos

- **fixture / `REPOSITORY_BACKEND=fixture`**: repos in-memory (comportamiento previo).
- **supabase**: estado durable en PostgreSQL vía `service_role`.

## Seguridad

RLS habilitado; `revoke all` para `anon` y `authenticated`. Solo backend escribe/lee.

## Flujo circuit breaker

```text
closed → (fallos ≥ umbral) → open → (retry_after) → half_open → (éxito) → closed
```
