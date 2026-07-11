# Guardrails de NexoMercado AI

## Producto

- Mantener exactamente dos agentes: Analista de Coyuntura y Asesor Financiero.
- Implementar búsqueda, normalización, cálculos, validación y almacenamiento como herramientas o servicios, no como agentes.
- No ejecutar compras o ventas, prometer rendimientos ni presentar asesoría personalizada.
- Tratar `uncertain` y `insufficient_evidence` como resultados válidos.
- Exigir revisión humana para compartir señales.

## Evidencia y cálculos

- Vincular toda afirmación financiera a evidencia, fuente, fecha y snapshot/hash.
- Obtener toda cifra desde una fuente o función determinística.
- Calcular confianza por código y conservar contradicciones.
- Contar publishers originales independientes, no agregadores, para corroboración.
- Mostrar `fixture`, `live` o `fallback`, proveedor efectivo y frescura.

## Seguridad

- Mantener claves de proveedores, OpenAI y Supabase privilegiadas fuera del frontend.
- No registrar secretos ni contenido sensible innecesario.
- Mantener operaciones idempotentes y revisiones inmutables.
- No autorizar mediante `user_metadata` cuando se implemente Supabase Auth/RLS.

## Gobierno

- Ejecutar una fase por invocación.
- No saltar prerrequisitos ni marcar una fase `aceptada` automáticamente.
- No hacer commit, push, despliegue o cambios cloud sin autorización explícita.
- Preservar cambios preexistentes y detenerse ante solapamientos.
