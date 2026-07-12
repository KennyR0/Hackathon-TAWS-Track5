# Guion de demo Fase 7

Fecha: 2026-07-12

## Objetivo

Mostrar que NexoMercado AI transforma eventos verificables en senales explicables, exige revision humana y produce un briefing trazable sin emitir recomendaciones de compra o venta.

## Preparacion local

Backend:

```powershell
MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
corepack pnpm dev
```

Smoke previo:

```powershell
MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py
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
- La demo deploy-ready ya tiene Vercel/Render configurados, pero no se hizo despliegue cloud real.
