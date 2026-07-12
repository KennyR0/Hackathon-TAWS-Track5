---
plan_version: 2
current_phase: 7
phase_S0: aceptada
phase_0: aceptada
phase_1: aceptada
phase_2: aceptada
phase_3: aceptada
phase_4: aceptada
phase_5: aceptada
phase_6: aceptada
phase_7: lista_para_revision
phase_8: pendiente
phase_9: pendiente
phase_10: pendiente
last_updated: 2026-07-12
---

# Plan de implementación por fases — NexoMercado AI

## 1. Objetivo y estrategia

Construir primero un MVP demostrable para el Track 5 y evolucionarlo después hacia una plataforma productiva de inteligencia de mercado. El producto convierte noticias y datos verificables en señales explicables, briefings y acciones de investigación, siempre sujetos a revisión humana.

Decisiones confirmadas:

- Estrategia híbrida `fixtures-first`: la demo debe funcionar sin servicios externos.
- Universo inicial: AAPL con benchmark SPY, BTC y petróleo/contexto macro.
- Usuario fijo `Analista Demo` durante el MVP.
- Frontend React + Vite + TypeScript.
- Backend Python 3.12 + FastAPI + Pydantic.
- Orquestación LangGraph con dos agentes principales y nodos especializados de control.
- Supabase PostgreSQL como persistencia.
- Vercel para frontend y Render para backend.
- Sin trading, recomendaciones personalizadas ni promesas de rendimiento.

## 2. Fuentes de verdad

- Arquitectura: [`referencias/ARQUITECTURA_GENERAL_NexoMercado_AI.md`](referencias/ARQUITECTURA_GENERAL_NexoMercado_AI.md)
- Requisitos del hackathon: [`referencias/Hackathon_Guide_Financial_Agents_IA_-_Track_5.md`](referencias/Hackathon_Guide_Financial_Agents_IA_-_Track_5.md)
- Estado, alcance y gates: este documento.

Precedencia ante conflictos:

1. Requisitos obligatorios del Track 5.
2. Contratos e invariantes aprobados en este plan.
3. Arquitectura general.
4. Skill `run-nexomercado-phase`.
5. Skills genéricas o recomendaciones de terceros.

## 3. Gobierno de fases

Estados válidos:

- `pendiente`
- `en_curso`
- `lista_para_revision`
- `aceptada`
- `ajustar`
- `descartada`
- `bloqueada`

Reglas:

- Solo una fase puede estar `en_curso` o `lista_para_revision`.
- Una fase no comienza hasta que todas sus predecesoras estén `aceptada`.
- Cada fase usa una rama `codex/fase-N-descripcion`.
- La skill puede dejar una fase `lista_para_revision`, pero no puede marcarla `aceptada` o `descartada` sin instrucción explícita del usuario.
- Ninguna invocación implementa más de una fase.
- No se hace commit, push, despliegue ni cambio cloud sin autorización explícita.
- Una alternativa rechazada no modifica el último baseline aceptado.
- Los cambios preexistentes del usuario se preservan; si se solapan con una fase, la ejecución se detiene y reporta el conflicto.
- Excepcion autorizada: Fase 6 ejecutada en `main` por autorizacion explicita del usuario.
- Excepcion autorizada: Fase 7 ejecutada en `main` por autorizacion explicita del usuario.

## 4. Estado

| Fase | Estado | Propósito |
|---|---|---|
| S0 | aceptada | Plan persistente y skills |
| 0 | aceptada | Contratos y fixtures |
| 1 | aceptada | Walking skeleton |
| 2 | aceptada | Radar |
| 3 | aceptada | Señal explicable |
| 4 | aceptada | Supabase, revisión y briefing |
| 5 | aceptada | Dos agentes y LangGraph |
| 6 | aceptada | Proveedores live y fallback |
| 7 | lista_para_revision | Despliegue y demo |
| 8 | pendiente | Auth, roles y RLS |
| 9 | pendiente | Workers y operación |
| 10 | pendiente | Diferenciadores |

Estado operativo actual del repositorio:

- `main` ya contiene un backend funcional `fixtures-first` con API, workflow, pruebas offline y validación de fases.
- La prioridad activa del equipo es cerrar la persistencia real server-side con Supabase sin romper el baseline offline.
- El orden de trabajo recomendado es:
  1. `main` estable;
  2. persistencia durable;
  3. frontend/demo visible;
  4. despliegue y entregables finales.

## 5. Arquitectura e interfaces aprobadas

### 5.1 Límites del sistema

- FastAPI es la única puerta de entrada a la lógica y proveedores financieros.
- El frontend no almacena secretos ni consume proveedores directamente.
- Los proveedores, cálculos y validaciones son servicios determinísticos o nodos especializados, no agentes financieros autónomos adicionales.
- Los dos agentes principales son `Analista de Coyuntura de Mercados IA` y `Asesor Financiero e Inversiones IA`.
- El Asesor solo recibe señales que superaron el validador de evidencia.
- El LLM no calcula precios, retornos, porcentajes, volatilidad, confianza ni estados.

### 5.2 Modos de datos

- `fixture`: snapshots locales reproducibles.
- `live`: proveedores reales.
- `fallback`: snapshot o caché usado tras una falla externa.

Cada respuesta debe incluir modo efectivo, proveedor, `retrievedAt`, `dataAsOf` y advertencias de frescura.

### 5.3 Contratos

Pydantic es la fuente de verdad. OpenAPI genera o valida los tipos TypeScript.

Enums:

- `Impact`: `positive | negative | neutral | uncertain`
- `AnalysisStatus`: `processing | completed | insufficient_evidence | failed`
- `ReviewStatus`: `pending_review | reviewed | escalated | discarded`
- `BriefingStatus`: `draft | shareable`
- `DataMode`: `fixture | live | fallback`
- `InstrumentType`: `equity | etf | crypto | commodity | macro | credit | other`
- `SourceTier`: `A | B | C | D`

Entidades:

- `Source`
- `Article`
- `Event`
- `Asset`
- `MarketSnapshot`
- `Claim`
- `Evidence`
- `Signal`
- `SignalReview`
- `Briefing`
- `AgentRun`

Trazabilidad obligatoria:

```text
claim → evidence → article/source → snapshot/hash
```

Nombres canónicos:

- `evidenceIds`
- `counterEvidenceIds`
- `suggestedResearchActions`
- `ReviewRequest.status`

### 5.4 API del MVP

- `GET /health`
- `GET /api/v1/events`
- `GET /api/v1/events/{eventId}`
- `POST /api/v1/analyses`
- `GET /api/v1/analyses/{runId}`
- `GET /api/v1/analyses/{runId}/stream`
- `GET /api/v1/signals`
- `GET /api/v1/signals/{signalId}`
- `GET /api/v1/signals/{signalId}/evidence`
- `POST /api/v1/signals/{signalId}/reviews`
- `GET /api/v1/signals/{signalId}/reviews`
- `POST /api/v1/briefings`
- `GET /api/v1/briefings/{briefingId}`
- `GET /api/v1/watchlists/demo-global`
- `GET /api/v1/runs/{runId}/steps`

Los POST de análisis, revisión y briefing exigen `Idempotency-Key`.

Eventos SSE:

- `id`
- `runId`
- `node`
- `status`
- `timestamp`
- `payload`

SSE soporta heartbeat y reconexión con `Last-Event-ID`.

### 5.5 Revisión y briefing

- Cada señal nace en `pending_review`.
- `reviewed`, `escalated` y `discarded` requieren justificación.
- `reviewedBy` y `reviewedAt` se generan en el servidor.
- Cada transición crea un registro inmutable y actualiza el estado actual en la misma transacción.
- Un briefing `draft` puede incluir pendientes o escaladas.
- Un briefing `shareable` solo incluye señales con análisis `completed` y revisión `reviewed`.
- Las descartadas y las de evidencia insuficiente nunca son compartibles.

### 5.6 Reglas cuantitativas iniciales

- AAPL: cierre anterior contra primer cierre posterior; benchmark SPY; volumen relativo de 20 sesiones.
- BTC: reacción de 24 horas y baseline de 30 días.
- WTI: cambio de 30 días como contexto, nunca como prueba automática de causalidad.
- Confianza: pesos `25/20/20/20/15` para calidad, corroboración, relación, coherencia y frescura.
- El ejemplo de arquitectura produce `0.86` antes de penalizaciones.
- Umbral de abstención: `0.60`.
- Penalizaciones iniciales: una fuente `-0.20`, contradicción material `-0.20`, histórico incompleto `-0.15`, fallback antiguo `-0.10`, relación indirecta `-0.10`, falta de fuente primaria esperable `-0.05`.
- Ticker ambiguo, única fuente débil, fecha inválida o ausencia total de histórico fuerzan `uncertain/insufficient_evidence`.

## 6. Fases del MVP

### Fase S0 — Plan y skills

Prerrequisitos: ninguno.

Entregables:

- Este plan persistente.
- Dos documentos fuente versionados.
- Skill externa `fastapi-python` auditada, fijada e instalada en el proyecto.
- Skill propia `run-nexomercado-phase` creada, validada y sincronizada globalmente.
- Validadores de fase y sincronización probados.
- Forward-tests de la skill.

Gate:

- Referencias copiadas byte a byte.
- Plan parseable y con una sola fase activa.
- Skill externa sin archivos o instrucciones rechazadas y fijada a commit/checksum.
- `quick_validate.py` aprobado.
- Scripts de la skill aprobados.
- Instalación global con el mismo manifiesto SHA-256 que la copia canónica.
- Casos de forward-test aprobados.

Evidencia de cierre:

- Rama de trabajo: `codex/fase-s0-plan-skills`.
- Referencias copiadas byte a byte:
  - Arquitectura: SHA-256 `d537c92a0a61c91c542d8b7b7de8da0dc56d3d7c70fb8e3edb4e9545d2e08c74`.
  - Guía Track 5: SHA-256 `700b64a8fa62722f15cfed68509ac3a8a103ac663ea1b6947606ff3721589571`.
- `fastapi-python` auditada e instalada desde el commit inmutable `05a71308897983093248d719a2ffa1bca61d0768`:
  - Árbol aceptado: únicamente `SKILL.md` y la licencia copiada desde la raíz del repositorio; sin scripts ni assets ejecutables.
  - `SKILL.md`: SHA-256 `29c6ca5e2bbfb51d40f0fb0afd998b13e23234e1f88c790b6e6a435c7eac55de`.
  - Licencia confirmada: Apache-2.0; SHA-256 `1eb85fc97224598dad1852b5d6483bbcf0aa8608790dcc657a5a2a761ae9c8c6`.
  - Procedencia y checksums registrados en `skills-lock.json`.
- Skill canónica `run-nexomercado-phase` creada con `skill-creator` y exactamente cinco archivos funcionales.
- `quick_validate.py`: `Skill is valid!`, usando PyYAML 6.0.2 en un entorno temporal ajeno al repositorio.
- `validate_phase.py`:
  - Aprobó `implement S0` en la rama correcta.
  - Rechazó `implement 0` porque S0 todavía no está `aceptada`.
  - Rechazó `--require-clean` ante cambios preexistentes.
  - Rechazó la validación en un repositorio distinto.
- `check_sync.py`:
  - Rechazó un espejo deliberadamente diferente.
  - Aprobó el espejo global instalado en `~/.agents/skills/run-nexomercado-phase`.
  - Manifiesto común SHA-256: `9203a6cd290d37eea9b8610391745e316d0b422a6b1c04c33eb4c50942ab880d`.
- Forward-tests con agentes frescos:

| Caso | Resultado |
|---|---|
| Fase 0 prematura | Bloqueada por prerrequisito S0 no aceptado |
| Validación legítima de S0 | Aprobada en solo lectura |
| Repositorio incorrecto | Bloqueado por identidad y ausencia del plan |
| Worktree sucio y solapado | Detectado; ejecución detenida sin cambios |
| Prueba deliberadamente fallida | Exit code `7`; S0 conservó estado no aceptado |
| Solicitud de avance automático | Rechazada; no se aceptó S0 ni se inició Fase 0 |

- No se hizo commit, push, despliegue ni cambio cloud.
- Resultado del gate: aprobado; S0 queda `lista_para_revision` y espera decisión del usuario.

### Fase 0 — Contratos y fixtures

Prerrequisito: S0 `aceptada`.

Entregables:

- Contratos Pydantic y OpenAPI.
- Matriz de aceptación.
- Fixtures reproducibles para Apple, Bitcoin y petróleo.
- Al menos dos publishers originales independientes.

Gate: contratos y fixtures validan sin que ningún consumidor invente campos.

### Fase 1 — Walking skeleton

Prerrequisito: Fase 0 `aceptada`.

Entregables:

- Frontend y backend ejecutables.
- Health check, configuración y cliente tipado.
- Navegación mínima para radar, detalle, briefing y auditoría.
- CI inicial.

Gate: instalación limpia, lint, tests y builds verdes.

Evidencia de cierre local:

- Rama de trabajo: `main`, por excepcion autorizada explicitamente por el usuario.
- Frontend conectado al backend local con `VITE_API_BASE_URL=/api` y proxy Vite hacia `http://127.0.0.1:8000`.
- Cliente frontend real en `frontend/src/lib/api.ts`, con adaptacion minima desde contratos FastAPI a modelos de pantalla.
- Vistas conectadas: Radar, Detalle de senal, Revision humana, Briefing y Auditoria.
- Documento de conexiones y pendientes: `docs/CONEXIONES_FRONTEND_BACKEND.md`.
- Validaciones ejecutadas:
  - `corepack pnpm build` en `frontend`: aprobado.
  - `.venv312\Scripts\python.exe backend\scripts\export_openapi.py --check`: aprobado.
  - `.venv312\Scripts\python.exe -m pytest backend\tests --basetemp .tmp\pytest -p no:cacheprovider`: `139 passed`, usando shim temporal de `python3` en `.tmp` para los tests que lo invocan en Windows.
  - Smoke local FastAPI: `/health`, eventos, senal/evidencia, revision, briefing draft y analisis con 13 pasos de auditoria aprobados.
- No se hizo commit, push, despliegue ni cambio cloud.
- Resultado del gate: aprobado; Fase 1 queda `lista_para_revision` y espera decision del usuario.

### Fase 2 — Radar

Prerrequisito: Fase 1 `aceptada`.

Entregables:

- Normalización, publisher original, URL/hash y deduplicación exacta.
- Agrupamiento básico de eventos.
- Fuente, fecha, activo relacionado y filtros por instrumento, activo y antigüedad.

Gate: Historia de Usuario 1 completa sin red.

Evidencia de auditoria:

- API `GET /api/v1/events` con filtros por activo y metadatos `fixture`.
- Normalizacion y diagnostico de fuentes en `FixtureRepository`.
- Cobertura en `backend/tests/api/test_runtime_api.py` y contratos de consumidores.
- Resultado: fase aceptada por autorizacion del usuario para continuar a Fase 6.

### Fase 3 — Señal explicable

Prerrequisito: Fase 2 `aceptada`.

Entregables:

- Relación evento-activo.
- Métricas, confianza y abstención determinísticas.
- Evidencia favorable y contradictoria.
- Gráfico, benchmark, supuestos, invalidaciones, acciones y disclaimer.

Gate: Historia de Usuario 2 completa y ninguna cifra sin snapshot o evidencia.

Evidencia de auditoria:

- Calculos deterministas de retornos, benchmark, volumen relativo, confianza y abstencion.
- Senales runtime reconstruidas desde fixtures con evidencia favorable y contradictoria.
- Cobertura en `backend/tests/contracts/test_runtime_logic.py` y API de senales/evidencia.
- Resultado: fase aceptada por autorizacion del usuario para continuar a Fase 6.

### Fase 4 — Supabase, revisión y briefing

Prerrequisito: Fase 3 `aceptada`.

Entregables:

- Migraciones y seed de organización, usuario demo y watchlist.
- Persistencia de eventos, señales, evidencia, revisiones, briefings y auditoría.
- RLS habilitado; sin grants para `anon/authenticated` durante el MVP.
- Revisión inmutable y briefing determinístico.

Gate: datos conservados tras reinicio, justificación obligatoria y reglas de publicación verificadas.

Evidencia de auditoria:

- `SupabaseRepository` persiste revisiones, briefings, corridas, pasos e idempotencia sobre el baseline fixture.
- Scripts server-side: `bootstrap_supabase.py`, `check_supabase_connection.py` y `check_supabase_persistence.py`.
- Cobertura en `backend/tests/repositories/test_supabase_repository.py` y contratos de configuracion Supabase.
- Resultado: fase aceptada por autorizacion del usuario para continuar a Fase 6.

### Fase 5 — Dos agentes y LangGraph

Prerrequisito: Fase 4 `aceptada`.

Flujo:

```text
obtener/normalizar
→ vincular
→ calcular
→ Agente Analista
→ validar evidencia
→ Agente Asesor
→ pending_review
```

Entregables:

- Adaptadores LLM `fixture` y OpenAI Responses API.
- Structured Outputs con `store: false`.
- Modelo configurable y auditado.
- SSE y auditoría por nodo.
- `AsyncPostgresSaver` con `runId` como `thread_id`.

Gate: recuperación desde checkpoint sin duplicados y ninguna señal inválida llega al Asesor.

Evidencia de auditoria:

- Workflow LangGraph con nodos de normalizacion, calculo, Analista, validacion, abstencion, Asesor y auditoria.
- Adaptadores `fixture` y OpenAI Responses API con salida estructurada y `store: false`.
- Gate de asesor estricto: solo senales `completed` pasan tras `abstention_guard`.
- Cobertura en tests API de analisis, stream/replay, contratos OpenAI y persistencia de pasos.
- Resultado: fase aceptada por autorizacion del usuario para continuar a Fase 6.

### Fase 6 — Proveedores live y fallback

Prerrequisito: Fase 5 `aceptada`.

Entregables:

- GDELT y Finnhub.
- Twelve Data para AAPL/SPY.
- CoinGecko para BTC.
- FRED para WTI.
- Caché, presupuesto, reintentos, circuit breaker y fallback.

Gate: recorrido live y caída simulada con advertencia y confianza reducida.

Decision de ejecucion:

- Fase 6 ejecutada en `main` por autorizacion explicita del usuario.
- El recorrido live real se soporta con `.env` local, pero no es obligatorio para cerrar el gate si no hay claves.
- El cierre exige recorrido offline, proveedores simulados, caida simulada, fallback visible y penalizacion de confianza.

Evidencia de cierre local:

- Auditoria S0-Fase 5: backend, contratos, Supabase, LangGraph, revision humana y SSE presentes en codigo y tests.
- `.venv312\Scripts\python.exe scripts\validate_phase.py implement 6 --repo .`: aprobado antes de cerrar el gate, usando excepcion documentada para `main`.
- `.venv312\Scripts\python.exe -m pytest backend\tests --basetemp .tmp\pytest -p no:cacheprovider`: `143 passed`.
- `MARKET_DATA_MODE=fixture .venv312\Scripts\python.exe backend\scripts\check_market_data_pipeline.py`: `effectiveDataMode=fixture`, `requestsUsed=0`.
- `MARKET_DATA_MODE=hybrid .venv312\Scripts\python.exe backend\scripts\check_market_data_pipeline.py`: `effectiveDataMode=fallback`, warnings de proveedores y claves faltantes, sin exponer secretos.
- Tests nuevos cubren proveedores live simulados, claves faltantes, error con retry, circuit breaker, presupuesto y penalizacion de confianza por fallback.
- No se hizo commit, push, despliegue ni cambio cloud.
- Resultado del gate: aprobado; Fase 6 queda `lista_para_revision` y espera decision del usuario.

### Fase 7 — Despliegue y demo

Prerrequisito: Fase 6 `aceptada`.

Entregables:

- Frontend en Vercel.
- Backend en Render.
- Persistencia en Supabase.
- CORS, secretos, logs, smoke tests, E2E y guion de demo.

Gate: flujo `radar → señal → evidencia → revisión → briefing`, fallback visible y criterios del Track 5 aprobados.

Decision de ejecucion:

- Fase 7 ejecutada en `main` por autorizacion explicita del usuario.
- No se hizo commit, push ni despliegue cloud real.
- Vercel y Render quedan configurados para Dashboard/CLI con URLs y secretos reales fuera del repositorio.

Evidencia de cierre local:

- `.venv312\Scripts\python.exe scripts\validate_phase.py implement 7 --repo .`: aprobado en `main` usando excepcion documentada.
- `.venv312\Scripts\python.exe -m pytest backend\tests --basetemp .tmp\pytest -p no:cacheprovider`: `146 passed`, `2 warnings`.
- `.venv312\Scripts\python.exe backend\scripts\export_openapi.py --check`: OpenAPI vigente.
- `.venv312\Scripts\python.exe backend\scripts\check_demo_flow.py`: recorrido `radar -> senal -> evidencia -> revision -> briefing` aprobado con `dataMode=fixture`.
- `corepack pnpm lint`: aprobado.
- `corepack pnpm build`: aprobado.
- `MARKET_DATA_MODE=fixture .\.venv312\Scripts\python.exe backend\scripts\check_backend_runtime.py`: `effectiveDataMode=fixture`, `requestsUsed=0`.
- `MARKET_DATA_MODE=hybrid .\.venv312\Scripts\python.exe backend\scripts\check_market_data_pipeline.py`: `effectiveDataMode=fallback` con warnings de proveedores/claves.
- `render.yaml`: sintaxis YAML inspeccionada y servicio web FastAPI presente.
- Backend agrega CORS restringido por `BACKEND_CORS_ORIGINS` y dependencia runtime `uvicorn`.
- Frontend acepta `VITE_API_BASE_URL` y `VITE_API_URL`, normaliza `/api`, y muestra `dataMode`/warnings en detalle, briefing y auditoria.
- Resultado del gate: aprobado; Fase 7 queda `lista_para_revision` y espera decision del usuario.

## 7. Evolución posterior

### Fase 8 — Auth, roles y RLS

- Supabase Auth y JWT verificado por FastAPI.
- Roles `analyst`, `senior_analyst`, `advisor`, `admin`.
- Grants mínimos y RLS por organización.
- La autorización nunca depende de `user_metadata`.

### Fase 9 — Workers y operación

- Ingesta programada, precios, macro, reconciliación y limpieza.
- Resiliencia completa, OpenTelemetry, métricas y alertas.

### Fase 10 — Diferenciadores

- Deduplicación semántica con pgvector.
- Eventos históricos similares.
- Snapshots ecuatorianos trazables.
- Continuidad conversacional y mayor cobertura de instrumentos.

## 8. Matriz mínima del Track 5

| Criterio | Fase |
|---|---|
| Noticias recientes, fuente y fecha | 2 |
| Relación noticia-instrumento | 2 |
| Filtros por instrumento, activo y antigüedad | 2 |
| Impacto y confianza | 3 |
| Comparación histórica o de precio | 3 |
| Evidencia, fuentes y disclaimer | 3 |
| Briefing con acciones de investigación | 4 |
| Revisada, escalada o descartada con justificación | 4 |
| Sin compras ni ventas; revisión humana | Transversal |

## 9. Estrategia de pruebas

Skill:

- Rechazo de fase sin prerrequisitos.
- Diferencia entre `implement` y `validate`.
- Detección de repositorio incorrecto.
- Preservación de worktree sucio.
- Fallo de pruebas sin autoaceptación.
- Bloqueo por hash local/global distinto.
- Bloqueo de commit, push o cloud no autorizado.

Producto:

- Unitarias de retornos, confianza, penalizaciones, deduplicación, abstención y estados.
- Contratos de proveedores, Pydantic, OpenAPI y TypeScript.
- Integración de migraciones, revisión, idempotencia, checkpoints y SSE.
- Antialucinación: evidencia inexistente, ticker ambiguo, cifra no respaldada, fecha futura, contradicción e histórico ausente.
- E2E de las tres historias, descarte, briefing compartible y fallback.

## 10. Supuestos y exclusiones del MVP

- Las fases S0–5 pueden trabajar sin claves de proveedores mediante fixtures.
- Supabase debe estar provisionado antes de aceptar la Fase 4.
- La Fase 6 soporta credenciales live; sin claves locales, su gate se cierra con mocks, fallback simulado y scripts listos para `.env`.
- La Fase 7 requiere autorización y acceso a Vercel y Render.
- La demo pública usa datos no sensibles y una identidad fija; no se considera producción.
- Quedan fuera: trading, personalización financiera, alta frecuencia, roles completos, móvil, correo, PDF y cobertura extensa de crédito.

## 11. Registro de decisiones

| Fecha | Fase | Decisión | Motivo |
|---|---|---|---|
| 2026-07-11 | S0 | Iniciar | Implementación autorizada por el usuario |
| 2026-07-11 | S0 | Fijar `fastapi-python` al commit `05a7130` | Evitar deriva de la dependencia y conservar procedencia verificable |
| 2026-07-11 | S0 | Registrar Apache-2.0 como licencia efectiva | La auditoría del árbol fijado corrigió la suposición inicial de licencia |
| 2026-07-11 | S0 | Mantener la copia del repositorio como canónica | El espejo global se puede reconstruir y validar por manifiesto SHA-256 |
| 2026-07-11 | S0 | Solicitar revisión | Todos los gates de S0 terminaron verdes; solo el usuario puede aceptarla |
| 2026-07-12 | 1 | Conectar frontend con backend solo local | Alcance elegido por el usuario; despliegue Vercel/Render queda pendiente |
| 2026-07-12 | 1 | Trabajar en `main` sin rama nueva | Excepcion autorizada explicitamente por el usuario |
| 2026-07-12 | 6 | Trabajar en `main` sin rama nueva | Excepcion autorizada explicitamente por el usuario para implementar proveedores live/fallback |
| 2026-07-12 | 6 | Cerrar live sin claves obligatorias | El gate acepta mocks, caida simulada y script live opcional para no exponer secretos |
| 2026-07-12 | 7 | Trabajar en `main` sin rama nueva | Excepcion autorizada explicitamente por el usuario para preparar demo deploy-ready |
| 2026-07-12 | 7 | No desplegar cloud real | Alcance elegido: configuracion versionada, smokes locales y guia de demo |

## 12. Registro de cambios

| Fecha | Versión | Cambio |
|---|---:|---|
| 2026-07-11 | 1 | Plan inicial persistido; Fase S0 en curso |
| 2026-07-11 | 2 | Skills auditadas y sincronizadas; forward-tests aprobados; S0 lista para revisión |
| 2026-07-12 | 2 | Fase 1 conectada localmente entre React/Vite y FastAPI; queda lista para revision |
| 2026-07-12 | 2 | Auditoria S0-Fase 5 registrada; Fase 6 iniciada en main por autorizacion explicita |
| 2026-07-12 | 2 | Fase 6 live/fallback implementada y lista para revision |
| 2026-07-12 | 2 | Fase 7 deploy-ready implementada y lista para revision |
