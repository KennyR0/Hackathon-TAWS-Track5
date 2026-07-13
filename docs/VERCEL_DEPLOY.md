# Despliegue del frontend en Vercel

Fecha: 2026-07-12

El frontend desplegable vive en `frontend/`, pero el repositorio tambien incluye `vercel.json` en la raiz para que Vercel pueda importar el repo completo sin perder la ruta correcta del build.

## Opcion recomendada: importar el repo completo

En Vercel, importa `KennyR0/Hackathon-TAWS-Track5` y deja el Root Directory en la raiz del repositorio.

La configuracion versionada en `vercel.json` usa:

- Install Command: `corepack enable && corepack pnpm --dir frontend install --frozen-lockfile`
- Build Command: `corepack enable && corepack pnpm --dir frontend build`
- Output Directory: `frontend/dist`
- Framework: Vite
- Rewrite SPA: `/(.*)` -> `/index.html`

## Opcion alternativa: Root Directory `frontend`

Si prefieres configurar el proyecto de Vercel con Root Directory `frontend`, Vercel usara `frontend/vercel.json`:

- Install Command: `corepack enable && corepack pnpm install --frozen-lockfile`
- Build Command: `corepack enable && corepack pnpm build`
- Output Directory: `dist`
- Rewrite SPA: `/(.*)` -> `/index.html`

## Variables de entorno en Vercel

Configura estas variables en el proyecto frontend de Vercel:

```text
VITE_API_BASE_URL=https://<render-service>/api
VITE_AUTH_ENABLED=false
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=<publishable-or-anon-key>
```

Notas:

- `VITE_API_BASE_URL` debe apuntar al backend publicado, normalmente Render.
- `VITE_AUTH_ENABLED=false` mantiene la presentación pública con identidad fija del MVP.
- Si activas auth con `VITE_AUTH_ENABLED=true`, tambien debes configurar Supabase Auth y sus redirect URLs para el dominio de Vercel.
- No cargues `OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY` ni claves de proveedores live en Vercel frontend; esas pertenecen al backend.

## CORS del backend

Cuando tengas el dominio final de Vercel, agregalo a `BACKEND_CORS_ORIGINS` en el backend:

```text
BACKEND_CORS_ORIGINS=https://<vercel-app>.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

## Validacion local antes de publicar

Desde `frontend/`:

```powershell
corepack pnpm install --frozen-lockfile
corepack pnpm build
```

La CLI de Vercel no esta instalada actualmente en este entorno. Para desplegar desde terminal, instala/autentica `vercel` o usa la importacion desde GitHub.
