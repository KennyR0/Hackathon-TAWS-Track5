# NexoMercado AI

Plataforma de inteligencia de mercado que transforma noticias y datos verificables en señales explicables y briefings sujetos a revisión humana.

## Qué hay hoy en el repo

- Backend FastAPI con contratos tipados y OpenAPI exportado.
- Workflow con dos agentes y nodos de control:
  - Analista de Coyuntura de Mercados IA
  - Asesor Financiero e Inversiones IA
- Modo `fixture` offline, modo `supabase` para persistencia mutable y modo `hybrid/live` para proveedores.
- Frontend React/Vite conectado al backend real para radar, señales, reviews, briefings y auditoría.
- Persistencia con Supabase para reviews, briefings, runs, steps e idempotencia.

El foco del proyecto es explicar por qué una señal existe, de dónde salen sus datos y qué necesita revisión humana antes de compartirse.

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
- [Guion de presentación](docs/demo-script.md)
- [Entrega para jurado](docs/ENTREGA_JURADO.md)

El repositorio trabaja por fases gobernadas en `docs/PLAN_IMPLEMENTACION_POR_FASES.md`. Ninguna fase se acepta o avanza automaticamente.

## Recorrido principal del producto

1. `GET /api/v1/events`: radar de eventos y filtros.
2. `GET /api/v1/signals` y `GET /api/v1/signals/{signalId}`: señales explicables por activo.
3. `GET /api/v1/signals/{signalId}/evidence`: trazabilidad y respaldo.
4. `POST /api/v1/signals/{signalId}/reviews`: revisión humana con justificación.
5. `POST /api/v1/briefings`: briefing `draft` o `shareable`.
6. `POST /api/v1/analyses` + SSE: ejecución del workflow y auditoría por pasos.

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

## Arranque rápido

### 1. Variables de entorno

```bash
cp .env.example .env
```

Valores mínimos para trabajar offline:

```bash
LLM_PROVIDER=fixture
REPOSITORY_BACKEND=fixture
MARKET_DATA_MODE=fixture
FIXTURE_BUNDLE_PATH=data/fixtures/v1/phase0_bundle.json
VITE_API_BASE_URL=/api
```

### 2. Backend

Instala dependencias del backend en Python 3.12:

```bash
cd backend
python -m pip install -e .[dev]
```

Levanta la API:

```bash
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

También puedes usar `pnpm` si lo prefieres. En desarrollo, Vite proxifica `/api` hacia `http://127.0.0.1:8000`.

### 4. Verificaciones útiles

Backend:

```bash
pytest backend/tests -q
python backend/scripts/check_demo_flow.py
python backend/scripts/check_backend_runtime.py --env-file .env
python backend/scripts/check_public_deployment.py --skip-browser
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run lint
npm run build
```

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
- `GDELT_API_KEY`, `FINNHUB_API_KEY`, `TWELVE_DATA_API_KEY`, `COINGECKO_API_KEY`, `FRED_API_KEY` y `EIA_API_KEY` para sourcing live opcional
- `RAPIDAPI_KEY`, `YAHOO_FINANCE_API_HOST` y `YAHOO_FINANCE_BASE_URL` para Yahoo Finance como backup e historicos
- `MARKET_PROVIDER_BUDGETS` para limites y reservas independientes por proveedor
- `GDELT_BASE_URL`, `GDELT_TIMEOUT_SECONDS`, `GDELT_MAX_ATTEMPTS`, `GDELT_CACHE_TTL_SECONDS` y `SEC_USER_AGENT` para endurecer el probe de noticias

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

Cadenas de respaldo:

- noticias: `GDELT -> Finnhub News -> cache -> fixture`
- acciones y ETF: `Twelve Data -> Finnhub -> Yahoo Finance/RapidAPI -> cache -> fixture`
- cripto: `CoinGecko -> Yahoo Finance/RapidAPI -> cache -> fixture`
- WTI: `FRED DCOILWTICO -> EIA RWTC -> cache -> fixture`

Los backups se activan ante clave ausente, presupuesto agotado, circuito abierto,
timeout, HTTP 401/403/429/5xx o payload invalido. YH Finance usa exclusivamente
`/api/v2/markets/stock/history` con `symbol`, `interval` y `limit`. La primera
integracion conserva el JSON crudo en `rawResponse`; no interpreta ni persiste OHLCV
hasta aprobar el contrato real del proveedor. No se usa `CL=F` como sustituto de WTI
porque un futuro no es equivalente al precio spot.
Twelve Data Basic ofrece actualmente 800 creditos diarios y cobra un credito por
simbolo incluso en batch; el ejemplo reserva 40 creditos:

```dotenv
MARKET_PROVIDER_BUDGETS={"twelve_data":{"period":"day","maxRequests":800,"safetyReserve":40}}
```

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
- `GDELT_CACHE_TTL_SECONDS` opcional
- `SEC_USER_AGENT` opcional
- `FINNHUB_API_KEY`
- `TWELVE_DATA_API_KEY`
- `FRED_API_KEY`
- `COINGECKO_API_KEY` opcional
- `EIA_API_KEY` opcional para el fallback WTI
- `RAPIDAPI_KEY`, `YAHOO_FINANCE_API_HOST` y `YAHOO_FINANCE_BASE_URL` opcionales pero requeridos en conjunto
- `YAHOO_FINANCE_HISTORY_PATH` opcional; por defecto `/api/v2/markets/stock/history`
- `GDELT_API_KEY` solo si el proveedor configurado lo requiere

## Fase 7: despliegue y presentación

La Fase 7 deja configuracion versionada para Vercel y Render. El proyecto ya cuenta con despliegues publicos verificados:

- Frontend: `https://hackathon-taws-track5.vercel.app/summary`
- Backend: `https://hackathon-taws-track5.onrender.com`

- Backend Render: [`render.yaml`](render.yaml) define un servicio FastAPI con `uvicorn`, health check `/health` y secretos `sync: false`.
- Frontend Vercel: [`vercel.json`](vercel.json) permite importar el repo completo y construir `frontend/`; [`frontend/vercel.json`](frontend/vercel.json) cubre la alternativa con Root Directory `frontend`.
- Guia Vercel: [`docs/VERCEL_DEPLOY.md`](docs/VERCEL_DEPLOY.md) documenta comandos, output directory, variables publicas y CORS.
- CORS backend: `BACKEND_CORS_ORIGINS` debe listar los origenes exactos permitidos, por ejemplo `https://<vercel-app>.vercel.app,http://localhost:5173`.
- Frontend publico: `frontend/.env.example` usa `VITE_API_BASE_URL=https://<render-service>/api`. Por compatibilidad tambien se acepta `VITE_API_URL`.
- Secretos: OpenAI, Supabase y proveedores live se configuran solo en el entorno backend.

Smoke local del flujo de presentación sin red ni secretos:

```powershell
MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py
```

Smoke publico de solo lectura:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\check_public_deployment.py
```

## Frontend actual

La SPA vive en `frontend/src/app`, `frontend/src/features` y `frontend/src/shared`.

Pantallas disponibles:

- `/summary`
- `/radar`
- `/assets/:symbol`
- `/signals`
- `/signals/:signalId`
- `/reviews`
- `/briefings`
- `/briefings/:briefingId`
- `/assistant`
- `/audit`
- `/audit/:runId`

Notas de contrato:

- El detalle de activo se deriva desde señales, eventos y snapshots existentes; hoy no hay endpoint profundo por activo.
- El asistente no envía chat libre porque el backend no expone ese endpoint todavía.
- La auditoría usa SSE real y replay de pasos persistidos.
