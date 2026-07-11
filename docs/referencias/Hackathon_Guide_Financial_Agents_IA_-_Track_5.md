# GUÍA DE DESARROLLO
## Hackathon de Agentes Financieros IA
### Track 5

Historias de usuario y criterios mínimos para productos funcionales en 48 horas

*Julio de 2026*

---

## Regla de alcance para todos los equipos

Cada producto debe cumplir, como mínimo, con los requisitos y criterios de aceptación definidos para su track. Los equipos pueden agregar funcionalidades, automatizaciones, integraciones o experiencias que consideren necesarias, siempre que no eliminen ni sustituyan el alcance mínimo requerido.

### Condiciones de demostración

- [ ] Se permiten datos ficticios, archivos de prueba e integraciones simuladas si el flujo funcional se puede demostrar de extremo a extremo.
- [ ] Las acciones reguladas o sensibles deben quedar como propuesta, alerta o solicitud de aprobación; no es necesario ejecutarlas en producción.
- [ ] Cada equipo conserva libertad creativa sobre interfaz, canal, tecnología y funcionalidades adicionales.

---

## Track 5: Inteligencia de Mercado y Recomendaciones Informadas por Noticias

**Agentes involucrados:** Analista de Coyuntura de Mercados IA; Asesor Financiero e Inversiones IA.

**Problema que resuelve:** Convierte noticias y datos verificables de mercado en señales explicables sobre renta variable, instrumentos de crédito, criptoactivos y otros activos. Ayuda a priorizar el análisis sin ejecutar operaciones ni prometer rendimientos.

### Historia de Usuario 1: Radar de noticias y activos

**Como:** analista o inversionista

**Quiero:** consultar noticias recientes por activo, sector o tema macroeconómico

**Para que:** identifique eventos que puedan afectar instrumentos financieros relevantes

**Criterios de aceptación**

- [ ] El Analista de Coyuntura de Mercados IA muestra noticias recientes de al menos dos fuentes aprobadas o de un feed de prueba, con fuente y fecha.
- [ ] Relaciona cada noticia con uno o más instrumentos: acciones, instrumentos de crédito, criptoactivos u otros activos.
- [ ] Permite filtrar por tipo de instrumento, activo y antigüedad de la información.

### Historia de Usuario 2: Señal explicable de impacto

**Como:** persona que analiza oportunidades de mercado

**Quiero:** recibir una señal sobre el posible impacto de una noticia

**Para que:** pueda priorizar qué investigar antes de tomar una decisión

**Criterios de aceptación**

- [ ] Clasifica el posible impacto como positivo, negativo, neutral o incierto e indica su nivel de confianza.
- [ ] Compara el evento con el movimiento de precio o información histórica de datos reales o de prueba.
- [ ] Explica la señal con evidencia y fuentes, y aclara que no constituye asesoría personalizada ni garantiza resultados.

### Historia de Usuario 3: Briefing de mercado con revisión humana

**Como:** asesor de inversiones o analista de mercado

**Quiero:** revisar un briefing con noticias, movimientos y acciones de investigación sugeridas

**Para que:** pueda validar el análisis antes de compartirlo con un cliente

**Criterios de aceptación**

- [ ] Genera un resumen por lista de seguimiento o instrumento con la noticia, movimiento asociado y posible acción de investigación.
- [ ] Permite marcar cada señal como revisada, escalada o descartada y guardar la justificación del analista.
- [ ] No ejecuta compras ni ventas: crea alertas o tareas para revisión humana.

### Productos similares en el mercado

- [Google Finance](https://www.google.com/finance/)
- [CoinMarketCap: Bitcoin](https://coinmarketcap.com/currencies/bitcoin/)
