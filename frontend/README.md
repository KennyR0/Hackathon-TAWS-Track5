# Frontend de NexoMercado AI

SPA en React + Vite para el Track 5 del hackathon. Consume el backend FastAPI real, muestra el modo de datos (`fixture`, `live`, `fallback`) y prioriza trazabilidad, revisión humana y auditoría.

## Stack

- React 19
- React Router 7
- TanStack Query
- TypeScript
- Recharts
- Lightweight Charts
- OpenAPI types generados desde `../contracts/openapi.json`

## Pantallas principales

- `/summary`: resumen operativo
- `/radar`: eventos y filtros
- `/assets/:symbol`: detalle derivado por activo
- `/signals`: cola de señales
- `/signals/:signalId`: detalle de señal con evidencia y revisión
- `/reviews`: centro de revisión humana
- `/briefings`: lista de briefings recientes
- `/briefings/:briefingId`: detalle de briefing y tareas embebidas
- `/assistant`: contexto del workflow y estado del run
- `/audit`: runs recientes
- `/audit/:runId`: timeline del workflow con SSE

## Configuración

Variables públicas:

```bash
VITE_API_BASE_URL=/api
```

Para despliegue:

```bash
VITE_API_BASE_URL=https://<render-service>/api
```

El frontend también acepta `VITE_API_URL` por compatibilidad, pero normaliza siempre al prefijo `/api`.

## Desarrollo local

Con `npm`:

```bash
npm install
npm run dev
```

Con `pnpm`:

```bash
pnpm install
pnpm dev
```

En local, Vite proxifica `/api` hacia `http://127.0.0.1:8000`.

## Scripts

```bash
npm run generate:types
npm run typecheck
npm run lint
npm run build
```

`build` regenera tipos OpenAPI antes de compilar.

## Estructura

```text
src/
  app/        shell, router y providers
  features/   vistas por dominio
  shared/     api, mappers, ui y utilidades
  lib/        auth publica de Supabase cuando `VITE_AUTH_ENABLED=true`
```

La ruta activa del proyecto vive en `src/app`, `src/features` y `src/shared`. La carpeta `src/lib` se conserva solo para la integración pública de Auth/Supabase usada por el cliente API.

## Límites actuales del contrato backend

- No existe un endpoint profundo de series por activo; `/assets/:symbol` se deriva desde señales y eventos existentes.
- No existe un endpoint de chat libre; `/assistant` muestra contexto real, prompts sugeridos y el progreso del workflow, sin simular conversación falsa.
- La auditoría usa SSE real en `/api/v1/analyses/{runId}/stream` y rehidratación con `/api/v1/runs/{runId}/steps`.
