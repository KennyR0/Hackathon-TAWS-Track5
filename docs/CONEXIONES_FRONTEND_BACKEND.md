# Conexiones frontend-backend

Fecha: 2026-07-13

## Alcance Fase 7

La Fase 7 dejó el proyecto listo para presentación pública con frontend en Vercel y backend en Render. Las URL públicas actuales son:

- Frontend: `https://hackathon-taws-track5.vercel.app/summary`
- Backend: `https://hackathon-taws-track5.onrender.com`

Los secretos siguen fuera del repositorio y se cargan únicamente en el entorno backend.

Excepcion autorizada: Fase 7 ejecutada en `main` por autorizacion explicita del usuario.

## Configuracion local

Backend:

```powershell
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

Variable publica local:

```text
VITE_API_BASE_URL=/api
```

En desarrollo, Vite proxifica `/api` hacia `http://127.0.0.1:8000`. Las claves privilegiadas de OpenAI, Supabase y proveedores de mercado siguen siendo solo del backend.

## Configuracion Vercel y Render

Frontend:

- `vercel.json` permite importar el repo completo en Vercel y construir `frontend/`.
- `frontend/vercel.json` cubre el caso alternativo donde el Root Directory del proyecto Vercel sea `frontend`.
- Ambos archivos definen fallback SPA a `/index.html`.
- `frontend/.env.example` documenta `VITE_API_BASE_URL=https://<render-service>/api`.
- El cliente tambien acepta `VITE_API_URL` por compatibilidad y normaliza siempre al prefijo `/api`.
- La guia completa esta en `docs/VERCEL_DEPLOY.md`.

Backend:

- `render.yaml` define el servicio FastAPI con `uvicorn app.main:app --app-dir backend`.
- `BACKEND_CORS_ORIGINS` lista origenes exactos permitidos, separados por coma.
- `OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY` y claves de proveedores live quedan como variables backend con `sync: false`.
- El modo fixture sigue siendo el default offline.

Ejemplo de CORS para presentación:

```text
BACKEND_CORS_ORIGINS=https://<vercel-app>.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

## Pantallas conectadas

| Pantalla | Endpoint | Conexion |
|---|---|---|
| Radar | `GET /api/v1/events` | Lista eventos y filtros `instrumentType`, `asset`, `publishedAfter`. |
| Detalle de senal | `GET /api/v1/signals/{signalId}` y `GET /api/v1/signals/{signalId}/evidence` | Muestra impacto, confianza, revision, evidencia, `dataMode` y warnings. |
| Revision humana | `POST /api/v1/signals/{signalId}/reviews` | Guarda `reviewed`, `escalated` o `discarded` con justificacion e `Idempotency-Key`. |
| Briefing | `POST /api/v1/briefings` | Crea briefing `draft`, hidrata senales y expone warnings agregados. |
| Auditoria | `POST /api/v1/analyses`, `GET /api/v1/analyses/{runId}`, `GET /api/v1/runs/{runId}/steps`, `GET /api/v1/analyses/{runId}/stream` | Crea una ejecucion, escucha SSE real, rehidrata pasos y renderiza modo de datos, warnings y timeline. |

## Smoke local de presentación

```powershell
MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py
```

Este smoke recorre `radar -> senal -> evidencia -> revision -> briefing` usando `TestClient`, sin red ni secretos.

## Smoke público

```powershell
.\.venv312\Scripts\python.exe backend\scripts\check_public_deployment.py
```

Por defecto el smoke público es de solo lectura: valida Vercel, Render, CORS, eventos, señales, evidencia, estado de proveedores y carga visual de `/summary`. Para probar escrituras controladas de análisis, revisión y briefing se debe pasar `--include-write-flow`.

## Limitaciones pendientes

- Auth productivo puede activarse con Supabase, pero la presentación pública actual usa identidad fija del MVP.
- No existe endpoint profundo por activo; esa pantalla se deriva desde señales y eventos existentes.
- No existe endpoint de chat libre; la pantalla `assistant` muestra contexto del run sin simular conversación.
