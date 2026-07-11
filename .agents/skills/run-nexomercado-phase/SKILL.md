---
name: run-nexomercado-phase
description: Ejecuta y valida exactamente una fase del plan de NexoMercado AI. Usar cuando se pida implementar, continuar, validar, revisar, ajustar o cerrar una fase en el repositorio Hackathon-TAWS-Track5; aplica prerrequisitos, límites de alcance, pruebas, evidencia y revisión humana sin avanzar automáticamente.
---

# Ejecutar una fase de NexoMercado

## Flujo obligatorio

1. Localizar la raíz con `git rev-parse --show-toplevel` y comprobar `docs/PLAN_IMPLEMENTACION_POR_FASES.md` y el título `NexoMercado AI`.
2. Leer el frontmatter, la sección de la fase solicitada y sus gates. No cargar fases posteriores salvo para comprobar que no estén activas.
3. Ejecutar `scripts/validate_phase.py <implement|validate> <fase> --repo <raíz>` antes de actuar.
4. Inspeccionar `git status --short` y preservar cambios preexistentes. Detenerse si se solapan con el alcance de la fase.
5. Para `implement`, trabajar únicamente en una rama `codex/fase-*` y cambiar el estado a `en_curso` antes de modificar producto.
6. Implementar solo los entregables enumerados. Si la fase toca FastAPI, leer `../fastapi-python/SKILL.md` y subordinarla a los contratos del repositorio.
7. Aplicar las skills instaladas de Supabase, OpenAI, React, pruebas o despliegue solo cuando el alcance de la fase las active, notificándolo al usuario.
8. Ejecutar las pruebas y el gate definidos. Registrar comandos, resultados y limitaciones en el plan.
9. Si el gate pasa, dejar la fase en `lista_para_revision`. Si falla, mantenerla `en_curso`, `ajustar` o `bloqueada` según la evidencia.
10. Finalizar la invocación. No aceptar la fase ni comenzar otra sin una decisión explícita del usuario.

## Modos

### `implement`

- Autorizar cambios solo dentro del alcance de una fase activa.
- Exigir predecesoras `aceptada`, fase `en_curso`, rama `codex/fase-*` y una única fase activa.
- No hacer commit, push, despliegue o cambios cloud salvo solicitud explícita.

### `validate`

- Ejecutar inspecciones y pruebas sin modificar código de producto.
- Admitir fases `en_curso`, `lista_para_revision` o `aceptada`.
- Reportar incumplimientos sin corregirlos salvo que el usuario cambie explícitamente a `implement`.

## Precedencia

Aplicar, en este orden:

1. Guía del Track 5.
2. Plan, contratos e invariantes del repositorio.
3. Arquitectura general.
4. Esta skill.
5. Skills genéricas y documentación externa.

Ante un conflicto, obedecer la fuente de mayor precedencia y registrar la decisión.

## Recursos

- Leer `references/guardrails.md` cuando la fase toque señales, evidencia, agentes, revisiones, secretos o proveedores.
- Ejecutar `scripts/validate_phase.py` para validar el estado y los prerrequisitos.
- Ejecutar `scripts/check_sync.py` después de crear o actualizar la copia global de esta skill.
