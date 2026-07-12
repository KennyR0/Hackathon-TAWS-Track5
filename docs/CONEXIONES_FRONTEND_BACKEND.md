# Conexiones frontend-backend locales

Fecha: 2026-07-12

## Alcance

Esta integracion conecta el frontend React/Vite con el backend FastAPI local usando datos `fixture`. No incluye despliegue en Vercel/Render ni credenciales live.

Excepcion autorizada: el trabajo se hizo sobre `main` sin crear una rama `codex/fase-1-*`, por autorizacion explicita del usuario para esta fase local.

## Configuracion local

Backend:

```powershell
cd backend
..\.venv312\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
corepack pnpm dev
```

Variable publica del frontend:

```text
VITE_API_BASE_URL=/api
```

En desarrollo, Vite proxifica `/api` hacia `http://127.0.0.1:8000`. Las claves privilegiadas de OpenAI, Supabase y proveedores de mercado siguen siendo solo del backend.

## Pantallas conectadas

| Pantalla | Endpoint local | Conexion |
|---|---|---|
| Radar | `GET /api/v1/events` | Lista eventos reales del fixture y usa filtros `instrumentType`, `asset` y `publishedAfter`. |
| Detalle de senal | `GET /api/v1/signals/{signalId}` y `GET /api/v1/signals/{signalId}/evidence` | Muestra impacto, confianza, revision, evidencia, supuestos, invalidaciones y acciones desde el contrato backend. |
| Revision humana | `POST /api/v1/signals/{signalId}/reviews` | Guarda `reviewed`, `escalated` o `discarded` con justificacion obligatoria e `Idempotency-Key`. |
| Briefing | `POST /api/v1/briefings` | Crea un briefing `draft` local para `watchlist_demo_global` usando las senales disponibles. |
| Auditoria | `POST /api/v1/analyses`, `GET /api/v1/analyses/{runId}`, `GET /api/v1/runs/{runId}/steps` | Crea una ejecucion fixture, espera estado terminal y renderiza pasos reales del run. |

## Mapeo de campos

| UI | Contrato backend |
|---|---|
| `Event.headline` | `EventView.event.title` |
| `Event.mainArticle` | Primer `EventView.articles[]` + `EventView.sources[]` por `sourceId` |
| `Event.assets[]` | `EventView.event.relatedAssets[]` |
| `Signal.status` | `Signal.analysisStatus` |
| `Signal.reviewStatus` | `Signal.review.status` |
| `Signal.confidenceScore` | `Signal.confidence` |
| `Signal.marketSnapshot.change24h` | `Signal.priceReaction.assetReturn * 100` |
| `Signal.marketSnapshot.benchmarkChange24h` | `Signal.priceReaction.benchmarkReturn * 100` cuando existe |
| `Signal.claims[]` | `Signal.thesis` + `Evidence.claim` |
| `Signal.evidences[]` | `Evidence[]` del endpoint de evidencia |
| `Briefing.summary` | `Briefing.executiveSummary` |
| `Briefing.signals[]` | `Briefing.prioritizedSignals[].signalId` hidratado con `GET /signals/{id}` |
| `AgentRun.steps[]` | `AgentRunStep[]` desde `/runs/{runId}/steps` |

## Conexiones no cerradas

- Despliegue Vercel/Render: fuera del alcance elegido; falta configurar URLs publicas y ejecutar smoke remoto.
- CORS productivo: no se agrego porque el flujo local usa proxy de Vite; debe restringirse al dominio del frontend cuando exista.
- Proveedores live: no se conectaron credenciales GDELT, Finnhub, Twelve Data, CoinGecko ni FRED.
- Supabase/Auth/RLS productivo: no se expuso al frontend ni se agrego login; sigue pendiente para fases posteriores.
- SSE visual en auditoria: se usa polling hasta estado terminal y luego `GET /runs/{runId}/steps`; el endpoint SSE queda disponible para una mejora posterior sin redisenar la vista.
- Generacion automatica de tipos TypeScript desde OpenAPI: el cliente mantiene una capa minima manual de contratos de transporte; la fuente de verdad sigue siendo Pydantic/OpenAPI.
