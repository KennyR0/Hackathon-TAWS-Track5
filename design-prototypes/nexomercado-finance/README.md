# NexoMercado Finance · Prototipo integral

Concepto visual aislado para evaluar una posible evolución del frontend de NexoMercado AI. No modifica la aplicación React, sus rutas, contratos, Supabase ni el backend.

## Ejecutar

Desde la raíz del repositorio:

```powershell
node design-prototypes/nexomercado-finance/server.mjs
```

Abrir `http://127.0.0.1:4175/`.

También puede servirse con cualquier servidor estático. Los módulos ES requieren HTTP; abrir `index.html` directamente mediante `file://` no es compatible.

## Recorrido sugerido

1. Comparar los temas claro y oscuro desde la barra superior.
2. Explorar un activo desde Panorama.
3. Abrir BTC-USD y revisar la contraevidencia.
4. Aprobar, escalar o descartar una señal; el cambio permanece en `localStorage`.
5. Crear una copia local del briefing.
6. Abrir Auditoría y recorrer el workflow.
7. Probar la búsqueda global con `AAPL`, `Bitcoin` o `crudo`.
8. Usar el asistente con las preguntas sugeridas.
9. Restaurar el estado inicial desde el pie de la navegación.

## Datos y límites

- Contenido derivado de `data/fixtures/v1/phase0_bundle.json`.
- 4 activos, 3 eventos, 3 señales, 12 evidencias, 1 briefing base y 1 ejecución.
- Las acciones son simulaciones locales; no realizan peticiones de red.
- No es una herramienta de inversión ni ofrece asesoría financiera.
- No utiliza logotipos, componentes ni identidad visual de Google.

## Archivos

- `index.html`: entrada y supuestos de diseño.
- `styles.css`: tokens, temas y layouts responsive.
- `data.js`: modelo reducido trazable al fixture.
- `app.js`: navegación, vistas e interacciones locales.
- `server.mjs`: servidor estático sin dependencias.
- `verify.mjs`: verificación headless de rutas, interacciones, viewports y capturas.
- `DECISION_MATRIX.md`: evaluación del frontend actual frente al concepto.
- `screenshots/`: capturas de verificación.
