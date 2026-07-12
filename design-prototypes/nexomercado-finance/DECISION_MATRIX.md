# Matriz de decisión · frontend actual vs. NexoMercado Finance

## Resultado ejecutivo

El concepto mejora de forma material la lectura financiera, la trazabilidad y la consistencia con el sistema de diseño documentado. La recomendación es **migrar progresivamente el lenguaje visual y el shell**, conservando la arquitectura React, contratos, queries y lógica funcional actuales.

No se recomienda reemplazar todo el frontend en un único cambio. El prototipo demuestra dirección de producto, no equivalencia técnica de producción.

## Comparación

Escala: 1 = deficiente, 3 = suficiente, 5 = sobresaliente. Las calificaciones son una evaluación heurística del código actual y del prototipo, no resultados de investigación con usuarios.

| Criterio | Frontend actual | Concepto | Evidencia observada |
|---|---:|---:|---|
| Claridad de jerarquía | 3 | 5 | El concepto separa mercado, investigación, operaciones y control; reduce héroes y tarjetas repetitivas. |
| Densidad informativa | 3 | 5 | Tablas, ledgers y metadatos permiten comparar más información sin perder estructura. |
| Confianza y procedencia | 4 | 5 | El actual ya conserva estados y fuentes; el concepto mantiene evidencia y revisión visibles junto a cada tesis. |
| Diferenciación de producto | 3 | 5 | El ledger de evidencia expresa el valor propio de NexoMercado en vez de parecer un dashboard de IA genérico. |
| Consistencia visual | 2 | 5 | El CSS actual usa gradientes, blur y radios que contradicen `docs/SISTEMA_DISENO.md`; el concepto aplica superficies planas y tokens semánticos. |
| Accesibilidad prevista | 4 | 4 | Ambos incluyen foco y estados; el concepto agrega skip link, landmarks y navegación responsive, pero aún requiere auditoría formal. |
| Responsividad | 3 | 4 | El concepto usa navegación inferior y sheets conceptuales; debe validarse después con contenido productivo variable. |
| Esfuerzo de adopción | 5 | 3 | Mantener lo actual no requiere migración. Adoptar el concepto implica reemplazar shell, tokens y varias composiciones visuales. |
| Compatibilidad funcional | 5 | 4 | El frontend actual está conectado al backend. El concepto conserva capacidades, pero sus acciones son locales. |

## Qué conservar

- React, React Router, TanStack Query y contratos OpenAPI.
- Mappers y view-models existentes.
- Estados de carga, error, frescura y modo de datos.
- Flujo maestro-detalle, SSE, permisos y persistencia real.
- Componentes de charts existentes cuando expresen datos reales.

## Qué migrar

1. Tokens de color, tipografía, radios, superficies y espaciado.
2. Shell: barra de comandos, navegación agrupada y asistente contextual plegable.
3. Resumen: strip de activos, tabla de señales y control humano compacto.
4. Señal: ledger de evidencia y consola de revisión en la misma vista.
5. Radar, Briefings y Auditoría: adoptar sus composiciones específicas en lugar de una tarjeta genérica compartida.
6. Tema claro predeterminado con tema oscuro equivalente y persistente.

## Riesgos de migración

- El prototipo usa contenido conocido; cadenas más largas y volúmenes reales pueden exigir virtualización o paginación.
- El panel de asistente compite por ancho en portátiles medianos y debe comportarse como overlay por debajo de 1180 px.
- Los tokens actuales están concentrados en un CSS grande; conviene migrarlos por capas y evitar una reescritura simultánea.
- La accesibilidad de charts y tablas necesita pruebas con lector de pantalla sobre los componentes React definitivos.

## Criterio de aceptación para adoptar

Adoptar el concepto si una prueba moderada con usuarios demuestra que:

- identifican una señal pendiente y su contradicción en menos de 30 segundos;
- distinguen dato fixture, dato de mercado y decisión humana sin explicación previa;
- completan una revisión y localizan su evidencia sin retrocesos;
- prefieren el concepto por claridad al compararlo con el frontend actual;
- el prototipo React mantiene accesibilidad AA y no degrada los tiempos de carga.

