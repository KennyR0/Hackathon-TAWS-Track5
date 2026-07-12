# Conexiones frontend-backend

Fecha: 2026-07-12

## Alcance Fase 7

La Fase 7 deja el proyecto listo para demo desplegable con frontend en Vercel y backend en Render, pero no ejecuta commit, push ni despliegue cloud real. Las URL publicas reales y los secretos se cargan fuera del repositorio.

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

Ejemplo de CORS para demo:

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

## Smoke local de demo

```powershell
MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py
```

Este smoke recorre `radar -> senal -> evidencia -> revision -> briefing` usando `TestClient`, sin red ni secretos.

## Limitaciones pendientes

- No se ejecuto despliegue real en Vercel ni Render.
- No se validaron URLs publicas reales porque aun no existen en el repo.
- Auth, roles y RLS productivo quedan para fases posteriores.
- No existe endpoint profundo por activo; esa pantalla se deriva desde señales y eventos existentes.
- No existe endpoint de chat libre; la pantalla `assistant` muestra contexto del run sin simular conversación.
