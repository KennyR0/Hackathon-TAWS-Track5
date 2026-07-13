# Entrega para jurado — NexoMercado AI

Fecha: 2026-07-13

## Resumen

NexoMercado AI convierte eventos de mercado y datos verificables en señales explicables, evidencia auditable, revisión humana y briefings trazables. El sistema no ejecuta trading, no promete rendimientos y no genera cifras financieras desde el LLM.

URLs públicas:

- Frontend: `https://hackathon-taws-track5.vercel.app/summary`
- Backend: `https://hackathon-taws-track5.onrender.com`

## Arquitectura

- Frontend React/Vite: panorama, radar, señales, revisión, briefings, asistente contextual y auditoría.
- Backend FastAPI: contratos Pydantic/OpenAPI, cálculos determinísticos, proveedores, persistencia y workflow.
- Supabase: estado mutable durable para reviews, briefings, runs, steps, conversaciones e idempotencia.
- Providers: modos `fixture`, `hybrid` y `live`, con fallback visible y warnings.
- OpenAI: usado solo en nodos de análisis estructurado; las cifras vienen de snapshots o cálculos del backend.

## Agentes y controles

El workflow mantiene exactamente dos agentes principales:

- `Analista de Coyuntura de Mercados IA`
- `Asesor Financiero e Inversiones IA`

Los demás pasos son nodos de control o servicios especializados: carga de contexto, normalización, verificación de fuentes, relación evento-activo, snapshots, cálculo, validación de evidencia, guardrail de abstención, guardrail de lenguaje de riesgo, briefing y auditoría.

## Qué es real hoy

- El frontend público está desplegado en Vercel.
- El backend público está desplegado en Render.
- Supabase persiste estado mutable real del flujo.
- El runtime puede consultar proveedores live cuando hay credenciales y presupuesto.
- La UI muestra `fixture`, `fallback` o `live` para no confundir procedencia.
- El endpoint `/api/v1/runtime/providers` debe devolver JSON auditable incluso si un proveedor o la store durable falla.

## Qué es controlado o fixture

- `/watchlists/demo-global`, `watchlist_demo_global` y `Analista Demo` son nombres contractuales del MVP para mantener un usuario/watchlist fijo.
- Los fixtures permiten reproducir la historia principal sin red ni secretos.
- Si un provider live falla, el backend responde `fallback` con warning y no presenta ese dato como live.

## Recorrido recomendado

1. Abrir `/summary` y mostrar panorama, activos, modo de datos y señales priorizadas.
2. Abrir `/radar` y filtrar eventos por activo o instrumento.
3. Entrar a una señal, revisar tesis, confianza, evidencia y snapshots.
4. Ejecutar revisión humana con justificación.
5. Generar o abrir un briefing `draft/shareable`.
6. Abrir auditoría y mostrar pasos del workflow, nodos de agentes y warnings.
7. Abrir `/assistant` y consultar proveedores para enseñar `live` vs `fallback`.

## Validaciones

Comandos principales:

```bash
python3 -m pytest backend/tests -q
cd frontend && npm run typecheck && npm run lint && npm run build
python3 backend/scripts/check_public_deployment.py
```

El smoke público es de solo lectura por defecto. Para probar escrituras controladas:

```bash
python3 backend/scripts/check_public_deployment.py --include-write-flow --write-timeout 180
```

## Mensaje clave

NexoMercado AI no intenta reemplazar criterio humano. Reduce ruido, explica señales, muestra límites de evidencia y deja un rastro auditable antes de que cualquier briefing sea compartible.
