# Estado técnico y prioridades del proyecto

Fecha de actualización: 2026-07-13

## Resumen ejecutivo

NexoMercado AI ya no está en fase de arranque. Hoy tiene un backend sólido, contratos estables, persistencia con Supabase para el estado mutable, modos `fixture/hybrid/live` y un frontend funcional conectado al contrato real del backend.

La prioridad actual no es replantear arquitectura. La prioridad es cerrar el producto para presentación pública: limpiar bordes, consolidar pruebas, validar el flujo real con Supabase y dejar una narrativa convincente para jurado.

## Calificación actual estimada

- **Cumplimiento del Track 5:** `8/10`
- **Madurez del backend:** `8/10`
- **Madurez del frontend:** `7/10`
- **Persistencia y operación real:** `6.5/10`
- **Proyecto completo para presentación de jurado:** `8.4/10`

## Qué ya está bien encaminado

### Backend

- API FastAPI modular.
- Contratos Pydantic y OpenAPI versionados.
- Endpoints de eventos, señales, evidencia, reviews, briefings, analyses, runs y SSE.
- Reglas determinísticas para métricas y confianza.
- Guardrails para abstención, lenguaje de riesgo y trazabilidad.
- Workflow con los dos agentes exigidos por el track.
- Soporte `fixture`, `supabase`, `hybrid` y `live`.

### Persistencia

- `SupabaseRepository` para estado mutable.
- Esquema SQL versionado en `supabase/schema.sql`.
- Persistencia de reviews, briefings, runs, steps e idempotencia.
- Scripts operativos para conexión, bootstrap y smoke.

### Frontend

- SPA en React/Vite con App Shell real.
- Query layer con TanStack Query.
- Tipos generados desde `contracts/openapi.json`.
- Pantallas de resumen, radar, señales, reviews, briefings, assistant y auditoría.
- SSE conectado a la auditoría del workflow.
- Visualización explícita de `dataMode`, warnings y estado de revisión.

## Qué falta realmente

### 1. Cierre operativo del backend

- Revalidar pruebas del backend en un entorno Python instalado y consistente.
- Confirmar el recorrido completo contra Supabase real, no solo por código y scripts.
- Seguir endureciendo errores, reintentos e inspección operativa.

### 2. Limpieza y consolidación del frontend

- Mantener la ruta activa en `frontend/src/app`, `frontend/src/features` y `frontend/src/shared`.
- Afinar responsive y microcopy final.
- Revisar el detalle de activo y assistant con enfoque de presentación.

### 3. Presentación end-to-end

- Probar el recorrido real:
  - radar
  - señal
  - evidencia
  - review
  - briefing
  - análisis con SSE
  - auditoría
- Verificar qué modo de datos se mostrará al jurado: `fixture` estable o `hybrid` con fallback visible.

### 4. Entrega

- README y docs actualizados.
- Deploy real en Render y Vercel.
- Documento final de entrega y guion de presentación bien alineados con lo que el sistema hace hoy.

## Riesgos actuales

### Riesgo alto

- Que el backend esté fuerte, pero la presentación no haga evidente el valor del sistema.
- Que el estado público de proveedores falle sin devolver warnings controlados.

### Riesgo medio

- Que Supabase esté configurado pero no validado a fondo en un recorrido real.
- Que el modo `live` se use en presentación sin suficiente control del fallback.

### Riesgo bajo

- Riesgo de arquitectura general. La base ya está lo bastante estable.

## Recomendación de prioridad

1. Validar backend + Supabase en flujo real.
2. Limpiar frontend legacy y cerrar detalles visuales.
3. Preparar deploy.
4. Ensayar el recorrido de presentación y congelar una historia principal.

## Conclusión

El proyecto ya tiene forma de producto serio. No está para volver a diseñarse desde cero; está para cerrarse, probarse bien y presentarse con claridad.

Si el equipo mantiene foco en presentación, consistencia operativa y narrativa, el repo ya tiene suficiente base para verse competitivo ante el jurado.
