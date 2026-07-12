# NexoMercado AI

Plataforma de inteligencia de mercado que transforma noticias y datos verificables en señales explicables y briefings sujetos a revisión humana.

## Documentación

- [Plan de implementación por fases](docs/PLAN_IMPLEMENTACION_POR_FASES.md)
- [Matriz de aceptación de la Fase 0](docs/FASE_0_MATRIZ_ACEPTACION.md)
- [Estado técnico y prioridades](docs/ESTADO_TECNICO_Y_PRIORIDADES.md)
- [Estructura del repositorio](docs/ESTRUCTURA_REPO.md)
- [Contrato OpenAPI](contracts/openapi.json)
- [Fixtures reproducibles](data/fixtures/v1/phase0_bundle.json)
- [Arquitectura general](docs/referencias/ARQUITECTURA_GENERAL_NexoMercado_AI.md)
- [Guía del Track 5](docs/referencias/Hackathon_Guide_Financial_Agents_IA_-_Track_5.md)
- [Conexiones frontend-backend](docs/CONEXIONES_FRONTEND_BACKEND.md)
- [Guion de demo](docs/demo-script.md)

El repositorio trabaja por fases gobernadas en `docs/PLAN_IMPLEMENTACION_POR_FASES.md`. Ninguna fase se acepta o avanza automaticamente.

## Estructura rápida del repo

```text
backend/app/         runtime principal del producto
backend/scripts/     scripts operativos del backend
backend/tests/       pruebas automatizadas
contracts/           openapi y contratos exportados
data/fixtures/       datos reproducibles del MVP
docs/                documentación viva del equipo
docs/referencias/    referencias base del proyecto
scripts/             scripts de gobernanza del repositorio
supabase/            esquema SQL y soporte de persistencia
```

La guía ampliada está en [docs/ESTRUCTURA_REPO.md](docs/ESTRUCTURA_REPO.md).

## Configuracion de OpenAI

La integracion del backend usa la API oficial de OpenAI a traves de variables de entorno. No guardes claves reales en el repositorio.

Variables esperadas:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` con valor sugerido `gpt-5.4`
- `OPENAI_REASONING_EFFORT` con uno de `minimal`, `low`, `medium` o `high`
- `LLM_PROVIDER` con `fixture` o `openai`
- `REPOSITORY_BACKEND` con `fixture` o `supabase`
- `MARKET_DATA_MODE` con `fixture`, `hybrid` o `live`
- `FIXTURE_BUNDLE_PATH` para seleccionar el bundle offline
- `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` solo para persistencia real
- `GDELT_API_KEY`, `FINNHUB_API_KEY`, `TWELVE_DATA_API_KEY`, `COINGECKO_API_KEY`, `FRED_API_KEY` para sourcing live opcional
- `GDELT_BASE_URL`, `GDELT_TIMEOUT_SECONDS`, `GDELT_MAX_ATTEMPTS` y `SEC_USER_AGENT` para endurecer el probe de noticias

Ejemplo rapido:

```bash
cp .env.example .env
export OPENAI_API_KEY="tu_api_key_nueva"
export OPENAI_MODEL="gpt-5.4"
export OPENAI_REASONING_EFFORT="medium"
export LLM_PROVIDER="fixture"
export REPOSITORY_BACKEND="fixture"
export MARKET_DATA_MODE="fixture"
export FIXTURE_BUNDLE_PATH="data/fixtures/v1/phase0_bundle.json"
```

Base de integracion agregada:

- Configuracion: `backend/app/config.py`
- Cliente OpenAI: `backend/app/openai_client.py`

## Modos de runtime del backend

### Modo fixture

Es el baseline estable del proyecto y no requiere credenciales externas.

```bash
cd backend
..\.venv312\Scripts\python.exe -m pytest tests --basetemp ..\.tmp\pytest -p no:cacheprovider
```

### Modo supabase

Mantiene lecturas deterministicas desde fixtures y persiste solo el estado mutable del flujo:

- reviews
- briefings
- runs
- run steps
- idempotencia

Antes de usarlo:

1. aplica [`supabase/schema.sql`](supabase/schema.sql) en tu proyecto Supabase;
2. configura `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` y `REPOSITORY_BACKEND=supabase`.

Comandos utiles:

```bash
.\.venv312\Scripts\python.exe backend\scripts\check_supabase_connection.py --env-file .env
.\.venv312\Scripts\python.exe backend\scripts\bootstrap_supabase.py --env-file .env --apply
.\.venv312\Scripts\python.exe backend\scripts\check_supabase_persistence.py --env-file .env
```

### Modo hybrid o live

El backend mantiene el contrato actual, pero puede intentar providers reales para el recorrido del track.

- `fixture`: todo offline y reproducible
- `hybrid`: intenta live y cae a `fallback`
- `live`: intenta live primero; si falla, responde con `fallback` y warnings

Probe operativo del runtime de mercado:

```bash
.\.venv312\Scripts\python.exe backend\scripts\check_market_data_pipeline.py --env-file .env
.\.venv312\Scripts\python.exe backend\scripts\check_backend_runtime.py --env-file .env
```

Variables live esperadas:

- `MARKET_DATA_MODE=hybrid` o `MARKET_DATA_MODE=live`
- `GDELT_BASE_URL` opcional
- `GDELT_TIMEOUT_SECONDS` opcional
- `GDELT_MAX_ATTEMPTS` opcional
- `SEC_USER_AGENT` opcional
- `FINNHUB_API_KEY`
- `TWELVE_DATA_API_KEY`
- `FRED_API_KEY`
- `COINGECKO_API_KEY` opcional
- `GDELT_API_KEY` solo si el proveedor configurado lo requiere

## Fase 7: demo deploy-ready

La Fase 7 deja configuracion versionada para Vercel y Render, pero no ejecuta commit, push ni despliegue cloud real.

- Backend Render: [`render.yaml`](render.yaml) define un servicio FastAPI con `uvicorn`, health check `/health` y secretos `sync: false`.
- Frontend Vercel: [`frontend/vercel.json`](frontend/vercel.json) mantiene fallback SPA a `index.html`.
- CORS backend: `BACKEND_CORS_ORIGINS` debe listar los origenes exactos permitidos, por ejemplo `https://<vercel-app>.vercel.app,http://localhost:5173`.
- Frontend publico: `frontend/.env.example` usa `VITE_API_BASE_URL=https://<render-service>/api`. Por compatibilidad tambien se acepta `VITE_API_URL`.
- Secretos: OpenAI, Supabase y proveedores live se configuran solo en el entorno backend.

Smoke local del flujo de demo sin red ni secretos:

```powershell
MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py
```
