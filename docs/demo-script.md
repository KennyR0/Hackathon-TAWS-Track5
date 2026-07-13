# Guion de presentación Fase 7

Fecha: 2026-07-13

## Objetivo

Mostrar que NexoMercado AI transforma eventos verificables en senales explicables, exige revision humana y produce un briefing trazable sin emitir recomendaciones de compra o venta.

## Preparacion local

Backend:

```powershell
$env:MARKET_DATA_MODE='fixture'; .\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
corepack pnpm dev
```

Smoke previo local:

```powershell
$env:MARKET_DATA_MODE='fixture'; .\.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py
```

## Presentación real híbrida

Este recorrido usa `backend/.env.local`, crea registros auditables con marcador técnico `DEMO_E2E` en
Supabase y consume OpenAI. No modifica el esquema ni presenta los fixtures de
señales como datos live.

Backend:

```powershell
.\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --env-file backend/.env.local --host 127.0.0.1 --port 8000
```

Frontend, en otra terminal:

```powershell
Set-Location frontend
corepack pnpm dev --host 127.0.0.1 --port 5173
```

Smoke HTTP real, con el backend activo:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\check_live_demo_flow.py --base-url http://127.0.0.1:8000 --analysis-timeout 180
```

Recorrido visual:

1. Abrir `http://127.0.0.1:5173/assistant` o elegir **Asistente IA**.
2. Pulsar **Consultar APIs ahora** y mostrar cada proveedor `live` o `fallback`.
3. Guardar un mensaje con marcador `DEMO_E2E:<id>` y confirmar que reaparece.
4. Pulsar **Iniciar análisis contextual** y esperar el estado terminal en Auditoría.
5. Mostrar los nodos `analyst_agent`, `advisor_agent` y `audit_writer`.

La presentación híbrida es válida si existe al menos un proveedor live y cada caída se
explica. Supabase u OpenAI fallidos invalidan el recorrido.

## Presentación pública

URLs actuales:

- Frontend: `https://hackathon-taws-track5.vercel.app/summary`
- Backend: `https://hackathon-taws-track5.onrender.com`

Smoke público de solo lectura:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\check_public_deployment.py
```

Smoke público con escrituras controladas:

```powershell
.\.venv312\Scripts\python.exe backend\scripts\check_public_deployment.py --include-write-flow --write-timeout 180
```

## Recorrido recomendado

1. Abrir el Radar.
   - Mostrar eventos por activo y filtros.
   - Recalcar que los datos pueden correr en `fixture`, `live` o `fallback`.

2. Entrar al detalle de la senal destacada.
   - Mostrar impacto, confianza, snapshot de mercado y modo de datos.
   - Si aparece fallback, leer las advertencias visibles.

3. Abrir la evidencia.
   - Mostrar la cadena `claim -> evidence -> article/source -> hash`.
   - Explicar que las cifras salen del backend y no del LLM.

4. Ejecutar revision humana.
   - Seleccionar `Escalar` o `Aprobar`.
   - Escribir una justificacion.
   - Confirmar que el backend guarda el cambio con `Idempotency-Key`.

5. Abrir Briefing Ejecutivo.
   - Mostrar resumen, senales priorizadas, pendientes de revision y acciones de investigacion.
   - Recalcar que un briefing `draft` puede contener pendientes o escaladas, pero un `shareable` exige revisiones aprobadas.

6. Abrir Auditoria.
   - Mostrar pasos del workflow, `dataMode`, duracion y warnings.
   - Explicar el flujo de agentes: normalizacion, calculo deterministico, Analista, validacion de evidencia, Asesor y controles.

## Mensajes clave

- No hay trading automatico ni recomendacion personalizada.
- El frontend no contiene secretos ni llama proveedores financieros directamente.
- El backend puede degradar a fallback y baja confianza cuando corresponde.
- La verificación live es una capa separada: radar, señales y evidencia histórica
  conservan su etiqueta fixture/fallback hasta implementar ingesta live completa.
- El despliegue público actual usa Vercel para frontend y Render para backend.
- `demo-global` y `Analista Demo` son nombres contractuales del MVP; no significan que el sistema invente datos.
