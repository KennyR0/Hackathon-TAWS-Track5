# Estructura del repositorio

Este documento fija la organizacion operativa actual de **NexoMercado AI** para que el equipo encuentre rapido cada pieza del proyecto.

## Mapa principal

| Ruta | Responsabilidad | Notas |
|---|---|---|
| `backend/app/` | Runtime principal del backend | API, servicios, repositorios, proveedores, workflow y contratos |
| `backend/app/api/` | Capa HTTP de FastAPI | Routers, dependencias y endpoints versionados |
| `backend/app/services/` | Casos de uso del backend | Orquesta reglas sin acoplarse al transporte |
| `backend/app/repositories/` | Persistencia y lectura del dominio | `fixture_repository` y `supabase_repository` |
| `backend/app/providers/` | Fuentes de datos de mercado | Fixtures y adapters live/hybrid |
| `backend/app/workflows/` | Orquestacion de agentes | Grafo, pasos y estado del run |
| `backend/app/llm/` | Adapters de modelos | Fixture y OpenAI Responses |
| `backend/app/calculations/` | Logica deterministica financiera | Retornos, benchmark, confianza y abstencion |
| `backend/app/contracts/` | Modelos y contratos tipados | Fuente de verdad para OpenAPI y validacion |
| `backend/scripts/` | Scripts operativos del backend | Health, bootstrap, smoke tests y exportes |
| `backend/tests/` | Suite automatizada | API, contratos, providers, fixtures y repositorios |
| `contracts/` | Artefactos consumibles por otros clientes | OpenAPI y campos de consumo |
| `data/fixtures/` | Datos reproducibles del MVP | Bundle canonico offline |
| `supabase/` | Esquema y soporte de persistencia durable | SQL base del overlay mutable |
| `docs/` | Documentacion viva del proyecto | Plan, estado tecnico, aceptacion y estructura |
| `docs/referencias/` | Referencias externas o fundacionales | Arquitectura general y guía del track |
| `scripts/` | Scripts de gobierno del repo | Validacion de fases y flujo de trabajo |

## Criterios de organizacion

### 1. Backend

- Todo codigo ejecutable del producto vive en `backend/app/`.
- Cada modulo debe pertenecer claramente a una sola capa:
  - `api`: transporte HTTP
  - `services`: casos de uso
  - `repositories`: acceso a datos y estado mutable
  - `providers`: sourcing externo o fixture
  - `workflows`: orquestacion multiagente
  - `calculations`: logica numerica pura
  - `contracts`: modelos publicos e internos tipados

### 2. Scripts

- `backend/scripts/` es para operaciones del sistema backend.
- `scripts/` en la raiz queda reservado para scripts de gobernanza del repo.
- Si un script toca runtime, providers, persistencia o backend, debe vivir en `backend/scripts/`.

### 3. Documentacion

- `docs/` contiene la documentacion activa del equipo.
- `docs/referencias/` solo guarda documentos de apoyo o arquitectura base.
- Si un documento describe el estado actual del repo, no debe ir en `referencias`.

## Variables de entorno por bloque

| Bloque | Variables activas |
|---|---|
| LLM | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_REASONING_EFFORT`, `LLM_PROVIDER` |
| Runtime | `REPOSITORY_BACKEND`, `MARKET_DATA_MODE`, `FIXTURE_BUNDLE_PATH` |
| Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| Market providers | `GDELT_API_KEY`, `GDELT_BASE_URL`, `GDELT_TIMEOUT_SECONDS`, `GDELT_MAX_ATTEMPTS`, `GDELT_CACHE_TTL_SECONDS`, `SEC_USER_AGENT`, `FINNHUB_API_KEY`, `TWELVE_DATA_API_KEY`, `COINGECKO_API_KEY`, `FRED_API_KEY` |

## Variables no usadas por el backend actual

Estas variables pueden existir en un `.env` local por conveniencia del equipo o por uso manual fuera del runtime, pero el backend actual no las consume:

- `SUPABASE_ANON_KEY`
- `SUPABASE_DB_PASSWORD`
- `SUPABASE_DB_URL`
- `SUPABASE_SECRET_KEY`

Si alguna de estas pasa a ser usada por el producto, debe agregarse explicitamente en `backend/app/config.py` y documentarse en `README.md` y `.env.example`.

## Regla practica para nuevas carpetas

Antes de crear una carpeta nueva, revisar:

1. si realmente representa una capa nueva;
2. si ya existe una carpeta con esa responsabilidad;
3. si obliga a duplicar contratos, scripts o documentacion.

La meta es mantener el repo pequeño en conceptos y claro en responsabilidades.
