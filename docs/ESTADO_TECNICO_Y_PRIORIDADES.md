# Estado tecnico y prioridades del proyecto

## Resumen ejecutivo

Este documento resume el estado real de **NexoMercado AI** frente a:

- los requisitos del **Hackathon de Agentes Financieros IA - Track 5**;
- la arquitectura aprobada del proyecto;
- el avance real observado en el repositorio.

Su objetivo es alinear al equipo sobre:

- que ya esta suficientemente bien encaminado;
- que falta para cumplir el minimo del track;
- que falta para que el proyecto se vea como una propuesta finalista;
- cual debe ser el orden tecnico de ejecucion.

---

## 1. Diagnostico general

### Calificacion actual estimada

- **Cumplimiento minimo del Track 5:** `7/10`
- **Madurez del backend:** `7.5/10`
- **Madurez del proyecto completo para jurado:** `6/10`

### Interpretacion

El proyecto ya cuenta con una base tecnica seria en backend, agentes, contratos, trazabilidad y pruebas offline. Sin embargo, todavia no esta completamente cerrado como producto integral porque faltan piezas importantes en:

- frontend demostrable;
- persistencia real en base de datos;
- despliegue publico y estable;
- documento final de entrega;
- narrativa de demo end-to-end.

---

## 2. Requisitos del hackathon y estado actual

| Requisito | Que pide el track | Estado actual | Observacion tecnica |
|---|---|---|---|
| Dos agentes obligatorios | Analista de Coyuntura de Mercados IA y Asesor Financiero e Inversiones IA | Alto | Ya existen en la arquitectura y workflow backend |
| Radar de noticias | Noticias con fuente y fecha | Parcial alto | Backend fuerte; falta consolidacion visual en frontend |
| Relacion noticia-activo | Cada noticia vinculada a instrumentos financieros | Alto | Ya existe logica backend y fixtures |
| Filtros | Tipo de instrumento, activo y antiguedad | Parcial alto | API lo soporta; falta UX integrada |
| Senal explicable | Impacto, confianza y explicacion | Alto | Backend lo soporta con reglas deterministicas |
| Comparacion con historico | Datos reales o de prueba | Alto | Ya existe logica sobre snapshots fixture |
| Evidencia y fuentes | Trazabilidad verificable | Alto | Es una de las fortalezas del proyecto |
| Revisión humana | reviewed, escalated, discarded con justificacion | Alto | Backend modelado; falta persistencia y UX madura |
| Briefing | Resumen para validacion humana | Parcial alto | Backend existe; falta experiencia visual completa |
| No trading | Solo alertas, tareas o propuesta | Alto | Guardrails bien alineados con el track |
| Demo end-to-end | Flujo demostrable completo | Medio | Todavia no completamente cerrado |
| Arquitectura solida | Backend separado de UI y logica auditable | Alto | Muy buen punto del proyecto |
| Mitigacion de alucinacion | No inventar cifras ni conclusiones inseguras | Muy alto | Una de las mejores partes del sistema |
| Tests automatizados | Evidencia de pruebas | Alto | Backend con pruebas passing offline |
| Despliegue | Link publico funcional | Bajo/pendiente | Falta cerrar |
| Documento final | Documento explicativo de entrega | Medio | Existe base documental, falta version final orientada a jurado |

---

## 3. Estado por componente

### 3.1 Backend

#### En que ya estamos bien

- API FastAPI funcional.
- Contratos tipados y OpenAPI.
- Endpoints principales para eventos, senales, evidencia, reviews, briefings y analyses.
- Repositorio `fixtures-first`.
- Calculos deterministas para impacto, benchmark, abnormal return y confianza.
- Workflow con LangGraph y dos agentes.
- Guardrails de riesgo, abstencion y evidencia.
- Pruebas backend corriendo en modo offline.

#### Que falta

- Persistencia real de reviews, briefings, runs y run steps.
- Repositorio real para Supabase/PostgreSQL.
- Endurecer mas el runtime de errores, idempotencia y concurrencia.
- Observabilidad mas visible para demo y operacion.
- Integracion con proveedores live o fallback real, si el tiempo alcanza.

#### Diagnostico

El backend ya esta en una etapa funcional seria para demo tecnica. No necesita reinventarse; necesita cerrarse operativamente.

**Nota estimada backend:** `7.5/10`

---

### 3.2 Frontend

#### Lo que deberia mostrar

- Radar de eventos y noticias.
- Filtros por instrumento, activo y antiguedad.
- Detalle de senal con impacto, confianza y evidencia.
- Vista de benchmarking o reaccion de mercado.
- Revisión humana por senal.
- Briefing por watchlist o instrumento.
- Auditoria o progreso del workflow.

#### Que falta

- App shell clara para analista.
- Integracion real con la API.
- Consumo de SSE para runs.
- Estados `loading`, `error`, `empty`, `processing`, `completed`.
- Presentacion clara de abstencion e `insufficient_evidence`.
- Flujo visual de `reviewed`, `escalated`, `discarded`.
- Briefing presentable para compartir.

#### Diagnostico

El frontend es actualmente una de las brechas principales del proyecto. El jurado va a percibir primero esta capa, por lo que aqui hay riesgo alto si no se cierra bien.

**Nota estimada frontend:** `4/10`

---

### 3.3 Base de datos

#### Lo que deberia existir

- Esquema real para:
  - fuentes;
  - articulos;
  - eventos;
  - activos;
  - snapshots;
  - evidence;
  - signals;
  - signal_reviews;
  - briefings;
  - review_tasks;
  - agent_runs;
  - run_steps.
- Foreign keys e indices minimos.
- Persistencia de historial inmutable para reviews.
- Persistencia de estados de briefings.
- Persistencia de workflow y auditoria.

#### Que falta

- Definicion final del schema relacional.
- Implementacion de repositorio real.
- Escritura/lectura durable de runs, reviews y briefings.
- Estrategia de idempotencia para operaciones POST.
- Auth y RLS en una fase posterior, si el tiempo alcanza.

#### Diagnostico

La base de datos esta bien pensada en arquitectura, pero todavia no esta madura en implementacion real dentro del flujo principal.

**Nota estimada base de datos:** `4/10`

---

### 3.4 Agentes y orquestacion

#### Fortalezas

- Los dos agentes requeridos por el track ya estan contemplados.
- Existen nodos especializados de verificacion, calculo, validacion, riesgo, briefing y auditoria.
- La arquitectura evita un LLM monolitico.
- Hay enfoque claro de abstencion segura.

#### Que falta

- Persistir journal y steps del run en almacenamiento real.
- Hacer visible en la demo por que paso cada nodo.
- Endurecer el handoff entre agentes con evidencia persistida.
- Mejorar la visibilidad del flujo para usuarios no tecnicos.

#### Diagnostico

La orquestacion es uno de los puntos mas fuertes del proyecto. El reto ya no es tanto tecnico, sino de presentacion y cierre operativo.

**Nota estimada agentes/orquestacion:** `8/10`

---

### 3.5 Mitigacion de riesgos y antialucinacion

#### En que estamos fuertes

- El LLM no calcula cifras financieras.
- Las metricas salen de funciones deterministicas.
- Toda afirmacion debe poder rastrearse a evidencia o snapshot.
- Existe abstencion cuando la confianza es baja o la evidencia es insuficiente.
- No hay ejecucion de compra/venta.
- Existe revision humana obligatoria.

#### Que falta

- Exponer estas garantias de forma muy clara en interfaz y demo.
- Hacer visible por que una senal fue marcada como incierta o insuficiente.
- Llevar esta narrativa al documento final y al pitch.

#### Diagnostico

Este es uno de los mejores argumentos competitivos del proyecto frente al jurado.

**Nota estimada mitigacion de riesgos:** `8.5/10`

---

## 4. Que ya esta suficientemente bien

Estas piezas no estan perfectas, pero ya tienen una base lo bastante buena como para dejar de discutir su direccion y comenzar a cerrarlas:

- arquitectura general del sistema;
- enfoque `fixtures-first`;
- separacion backend/logica/agentes;
- dos agentes alineados con el track;
- calculos deterministas y evidencia;
- flujo principal de señales, reviews y briefings en backend;
- pruebas offline del backend.

Estas areas ya no requieren replanteamiento profundo. Requieren cierre, integracion y pulido.

---

## 5. Que falta realmente para cumplir bien el proyecto

### Falta critica

1. **Cerrar frontend de demo**
   - radar;
   - detalle de senal;
   - evidencia;
   - reviews;
   - briefing;
   - run/auditoria.

2. **Cerrar persistencia real**
   - DB;
   - repositorios;
   - historial de revision;
   - runs y steps;
   - briefings persistidos.

3. **Cerrar flujo end-to-end**
   - iniciar analisis;
   - ver progreso;
   - revisar senal;
   - generar briefing;
   - compartir briefing.

4. **Cerrar entregables**
   - documento explicativo final;
   - deploy funcional;
   - video;
   - README orientado a demo.

### Falta importante pero no bloqueante para MVP minimo

- proveedores live;
- auth y RLS;
- observabilidad extendida;
- paneles mas avanzados;
- diferenciadores extra.

---

## 6. Prioridades tecnicas recomendadas

### Prioridad 1 - Producto demostrable

Objetivo: que el jurado vea el valor completo del sistema.

- construir o cerrar frontend operativo;
- conectar el frontend con la API real;
- mostrar evidencia, senales y estados;
- soportar el flujo de revision humana;
- mostrar briefing final.

### Prioridad 2 - Persistencia real

Objetivo: que el sistema se sienta serio y no efimero.

- modelar schema base;
- implementar repositorio real;
- persistir reviews, briefings, runs y steps;
- garantizar idempotencia minima.

### Prioridad 3 - Entrega

Objetivo: llegar bien a preseleccion.

- preparar documento final;
- preparar deploy funcional;
- preparar README y guia de prueba;
- definir demo script y video.

### Prioridad 4 - Extras competitivos

Objetivo: destacar frente a otros equipos.

- proveedor live con fallback;
- vista de auditoria atractiva;
- visualizacion clara de abstencion;
- explicabilidad mas fuerte.

---

## 7. Riesgos principales

### Riesgo 1 - Backend fuerte pero demo debil

Si el frontend no muestra con claridad el flujo, el jurado no percibira el valor del backend.

### Riesgo 2 - Sistema sin persistencia visible

Si todo parece temporal o en memoria, el producto puede sentirse menos serio.

### Riesgo 3 - Desalineacion entre documentos y estado real

Si la documentacion dice una cosa y la demo muestra otra, genera confusion en el equipo y debilita el discurso tecnico.

### Riesgo 4 - Falta de cierre en entregables

Aunque el sistema sea bueno, una entrega incompleta o poco clara puede afectar la preseleccion.

---

## 8. Recomendacion para el equipo

### Mensaje clave

No hace falta reinventar el proyecto.

Lo que hace falta es **cerrarlo** alrededor de un backend que ya tiene una buena base:

- interfaz clara;
- persistencia real;
- demo estable;
- entregables consistentes;
- narrativa fuerte de mitigacion de riesgos y explicabilidad.

### Enfoque recomendado

Trabajar en paralelo con ownership claro:

- **Backend:** persistencia, endurecimiento y live/fallback si alcanza.
- **Frontend:** radar, senal, evidencia, reviews, briefing y SSE.
- **DB:** schema y repositorio real.
- **Entrega:** documento, deploy, README, video y demo script.

---

## 9. Conclusiones

### Hoy ya esta fuerte

- backend core;
- agentes;
- trazabilidad;
- reglas cuantitativas;
- abstencion;
- pruebas offline.

### Hoy esta flojo

- frontend;
- base de datos real;
- persistencia end-to-end;
- despliegue;
- documento final de entrega.

### Veredicto

El proyecto **si tiene potencial real de finalista**, pero para que eso se note necesita cerrar rapido las capas visibles y operativas. La oportunidad no esta en cambiar la idea central, sino en convertir la buena base tecnica actual en una experiencia completa, estable y facil de demostrar.
