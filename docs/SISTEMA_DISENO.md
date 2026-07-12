# Sistema de Diseño Base — NexoMercado AI

Este documento define la base visual y estructural para la interfaz de **NexoMercado AI** (plataforma de inteligencia de mercado), siguiendo los lineamientos de la skill `interface-design` y `vercel-react-best-practices`.

---


## 1. Identidad Visual y Principios de Diseño

NexoMercado AI es una herramienta de análisis de alta intensidad. Su diseño se aleja del estilo común de "startup de IA genérica" (fondos azul eléctrico, bordes ultra redondeados, gradientes y chispas decorativas) y adopta una estética seria, de alta densidad informativa y centrada en el dato, inspirada en herramientas como **Google Finance** y terminales financieras.

### Reglas de Diseño Estrictas:
*   **Sin Azul Dominante:** No se utiliza el azul como color de fondo ni como color de acento principal. La base neutra es Grafito (oscuro) y Hueso (claro), con acentos de Ocre y Verde Bosque Profundo.
*   **Sin Gradientes ni Glassmorphism:** Todos los contenedores tienen fondos planos, opacos y bordes nítidos. La elevación y jerarquía se manejan mediante cambios sutiles de tono o sombras planas, nunca mediante desenfoques de fondo (backdrop-blur) o colores degradados.
*   **Bordes Sobrios (Poco Redondeados):** Los radios de borde son pequeños (máximo 6px) para dar una apariencia técnica, de "banco de trabajo".
*   **Alta Densidad:** Minimizar el espacio vacío innecesario. Los datos deben ser densos pero altamente legibles mediante el contraste tipográfico, el uso de fuentes monoespaciadas para números y alineaciones ópticas rigurosas.

---

## 2. Tokens de Diseño (CSS Variables & Tailwind Config)

### 2.1 Paleta de Colores — "Emerald & Amber Terminal"

La paleta ha evolucionado de una base gris neutra a un sistema cromático con carácter propio:
- **Base:** Grafito profundo cálido (dark mode por defecto, NO negro puro)
- **Acento primario:** Esmeralda (`#10B981` → `#34D399`) — crecimiento, positivo, acciones principales
- **Acento secundario:** Ámbar/Oro (`#F59E0B` → `#FCD34D`) — atención, incertidumbre, highlights
- **Semántico negativo:** Coral (`#EF4444` → `#FCA5A5`) — riesgo, errores, impacto negativo
- **Semántico neutro:** Pizarra (`#94A3B8` → `#CBD5E1`) — datos base, sin juicio

Cada sección tiene su propio **acento protagonista** para diferenciarse visualmente:
| Sección      | Color Acento  | Hex (dark)  | Propósito                        |
|-------------|---------------|-------------|----------------------------------|
| Radar       | Esmeralda     | `#10B981`   | Descubrimiento, scanning activo  |
| Señal       | Ámbar         | `#F59E0B`   | Análisis, atención focalizada    |
| Briefing    | Teal          | `#14B8A6`   | Comunicación, compartir          |
| Auditoría   | Cyan          | `#22D3EE`   | Técnico, consola, depuración     |

```css
/* frontend/src/index.css — DARK MODE (DEFAULT) */

:root {
  /* --- BASE (GRAFITO CÁLIDO) --- */
  --bg: #0C0F12;
  --surface-base: #141820;
  --surface-elevated: #1C2230;
  --border: rgba(255, 255, 255, 0.08);
  --border-focus: #94A3B8;

  /* --- TEXTO --- */
  --text-primary: #E2E8F0;
  --text-secondary: #94A3B8;
  --text-muted: #556270;

  /* --- SEMÁNTICOS --- */
  /* Positivo: Esmeralda vibrante */
  --status-positive-bg: rgba(16, 185, 129, 0.15);
  --status-positive-text: #34D399;

  /* Negativo: Coral cálido */
  --status-negative-bg: rgba(239, 68, 68, 0.15);
  --status-negative-text: #FCA5A5;

  /* Neutro: Pizarra fría */
  --status-neutral-bg: rgba(148, 163, 184, 0.12);
  --status-neutral-text: #CBD5E1;

  /* Incierto: Ámbar intenso */
  --status-uncertain-bg: rgba(245, 158, 11, 0.15);
  --status-uncertain-text: #FCD34D;

  /* --- ACCIÓN PRIMARIA: ESMERALDA --- */
  --action-accent: #10B981;
  --action-hover: #34D399;

  /* --- ACENTOS POR SECCIÓN --- */
  --accent-radar: #10B981;
  --accent-signal: #F59E0B;
  --accent-briefing: #14B8A6;
  --accent-audit: #22D3EE;
}

/* LIGHT MODE (clase .light) */
.light {
  --bg: #F8FAFB;
  --surface-base: #FFFFFF;
  --surface-elevated: #F1F5F9;
  --border: rgba(0, 0, 0, 0.10);
  --border-focus: #334155;

  --text-primary: #0F172A;
  --text-secondary: #475569;
  --text-muted: #94A3B8;

  --status-positive-bg: #DCFCE7;
  --status-positive-text: #166534;
  --status-negative-bg: #FEE2E2;
  --status-negative-text: #991B1B;
  --status-neutral-bg: #F1F5F9;
  --status-neutral-text: #475569;
  --status-uncertain-bg: #FEF3C7;
  --status-uncertain-text: #92400E;

  --action-accent: #059669;
  --action-hover: #047857;

  --accent-radar: #059669;
  --accent-signal: #D97706;
  --accent-briefing: #0D9488;
  --accent-audit: #0891B2;
}
```

### 2.2 Extensión de Configuración de Tailwind CSS

Si se utiliza Tailwind CSS, la extensión del tema se estructura mapeando directamente las variables CSS:

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        surface: {
          DEFAULT: 'var(--surface-base)',
          elevated: 'var(--surface-elevated)',
        },
        border: {
          DEFAULT: 'var(--border)',
          focus: 'var(--border-focus)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        status: {
          positive: {
            bg: 'var(--status-positive-bg)',
            text: 'var(--status-positive-text)',
          },
          negative: {
            bg: 'var(--status-negative-bg)',
            text: 'var(--status-negative-text)',
          },
          neutral: {
            bg: 'var(--status-neutral-bg)',
            text: 'var(--status-neutral-text)',
          },
          uncertain: {
            bg: 'var(--status-uncertain-bg)',
            text: 'var(--status-uncertain-text)',
          },
        },
        action: {
          accent: 'var(--action-accent)',
          hover: 'var(--action-hover)',
        }
      },
      borderRadius: {
        sm: '2px',
        md: '4px',
        lg: '6px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'monospace'],
      },
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '6': '24px',
        '8': '32px',
      }
    }
  }
}
```

---

## 3. Escala Tipográfica, de Espaciado y Radios

### 3.1 Escala Tipográfica (Basada en ratio ~1.2, optimizada para datos)

| Token tipográfico | Tamaño en px | Peso (Weight) | Uso recomendado | Clases CSS Equivalentes |
| :--- | :--- | :--- | :--- | :--- |
| `caption-sm` | 10px | 500 (Medium) | Micro-etiquetas, Tickers en tablas | `text-[10px] font-medium tracking-wider uppercase font-mono` |
| `caption` | 11px | 500 (Medium) | Etiquetas de inputs, badges de estado | `text-[11px] font-medium tracking-wide font-sans` |
| `body-sm` | 13px | 400 (Regular) | Celdas de tablas, metadatos, descripciones | `text-[13px] font-normal font-sans text-text-secondary` |
| `body` | 14px | 400 (Regular) | Lectura general, inputs, contenido principal | `text-[14px] font-normal font-sans text-text-primary` |
| `h4` | 16px | 600 (Semibold) | Títulos de tarjetas secundarias | `text-[16px] font-semibold font-sans tracking-tight` |
| `h3` | 18px | 600 (Semibold) | Títulos de secciones, paneles | `text-[18px] font-semibold font-sans tracking-tight` |
| `h2` | 22px | 600 (Semibold) | Títulos de vistas principales | `text-[22px] font-semibold font-sans tracking-tight` |
| `h1` | 26px | 700 (Bold) | Título de la app o vista central | `text-[26px] font-bold font-sans tracking-tight leading-none` |

> [!IMPORTANT]
> **Cifras y Datos Numéricos:** Cualquier valor numérico, precio, porcentaje o código de activo (ticker) debe renderizarse obligatoriamente con la fuente mono (`font-family: mono`) y con el estilo `font-variant-numeric: tabular-nums` para evitar el desplazamiento visual al cambiar los datos.

### 3.2 Escala de Espaciado y Radios de Borde

*   **Espaciado:** Multiplos de 4px.
    *   `4px` (`sp-1`): Espacios internos estrechos (gaps de badge, icono-texto).
    *   `8px` (`sp-2`): Gaps entre controles, padding vertical pequeño.
    *   `12px` (`sp-3`): Padding en botones, inputs y celdas de tabla densa.
    *   `16px` (`sp-4`): Padding interno de tarjetas y paneles.
    *   `24px` (`sp-6`): Distancia entre componentes y grupos principales.
    *   `32px` (`sp-8`): Margen exterior de la pantalla.
*   **Radios de Borde (Sobriedad técnica):**
    *   `2px` (`radius-sm`): Checkboxes, micro-badges, inputs de una celda.
    *   `4px` (`radius-md`): Botones, textareas, inputs estándar de formulario.
    *   `6px` (`radius-lg`): Tarjetas, diálogos/modales, barra de navegación.

---

## 4. Componentes Base Reutilizables (Átomo/Molécula)

### 4.1 Badge de Estado (Enum)

Este componente renderiza los estados de la cola de revisión (`ReviewStatus`) y el impacto de la señal (`Impact`). Utiliza colores desaturados y tipografía técnica para no sobrecargar el layout visualmente.

```
Intent:     Un analista financiero necesita saber de un vistazo el estado de una señal o noticia. Debe sentirse oficial e inobtrusivo, sin colores estridentes.
Hierarchy:  Elemento secundario de clasificación. Gana legibilidad por su contraste de color de texto sobre fondo, no por tamaño (11px).
Palette:    Semánticas desaturadas (positive, negative, neutral, uncertain) según el estado o impacto.
Depth:      Bordes planos y color sólido de fondo (sin sombras ni gradientes).
Surfaces:   Plano sobre la superficie contenedora actual.
Typography: caption (11px) · font-sans · font-medium.
Spacing:    padding horizontal de 6px (1.5 unidades de 4px) y vertical de 2px (0.5 unidades de 4px).
```

```tsx
// components/ui/StatusBadge.tsx
import React from 'react';

export type BadgeType = 
  | 'positive' | 'negative' | 'neutral' | 'uncertain' // Impact / Confianza
  | 'pending_review' | 'reviewed' | 'escalated' | 'discarded'; // ReviewStatus

interface StatusBadgeProps {
  type: BadgeType;
  label?: string;
}

const badgeConfig: Record<BadgeType, { bg: string; text: string; label: string }> = {
  positive: { bg: 'bg-status-positive-bg', text: 'text-status-positive-text', label: 'Positivo' },
  negative: { bg: 'bg-status-negative-bg', text: 'text-status-negative-text', label: 'Negativo' },
  neutral: { bg: 'bg-status-neutral-bg', text: 'text-status-neutral-text', label: 'Neutral' },
  uncertain: { bg: 'bg-status-uncertain-bg', text: 'text-status-uncertain-text', label: 'Incierto' },
  pending_review: { bg: 'bg-status-uncertain-bg', text: 'text-status-uncertain-text', label: 'Pendiente' },
  reviewed: { bg: 'bg-status-positive-bg', text: 'text-status-positive-text', label: 'Revisado' },
  escalated: { bg: 'bg-status-negative-bg', text: 'text-status-negative-text', label: 'Escalado' },
  discarded: { bg: 'bg-status-neutral-bg font-normal opacity-60', text: 'text-status-neutral-text', label: 'Descartado' },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, label }) => {
  const config = badgeConfig[type];
  return (
    <span
      className={`inline-flex items-center rounded-sm px-1.5 py-0.5 text-[11px] font-medium tracking-wide uppercase select-none ${config.bg} ${config.text}`}
    >
      {label || config.label}
    </span>
  );
};
```

---

### 4.2 Tabla de Datos Densa

Muestra listas de señales o eventos con un alto volumen de filas visibles por pantalla, maximizando la densidad informativa.

```
Intent:     Un analista de mercados necesita comparar y escanear rápidamente múltiples señales de activos en una sola vista.
Hierarchy:  El ticker (ej. AAPL) y el precio lideran. El resto de las columnas se demotan visualmente mediante pesos de texto y colores grisáceos.
Palette:    Fondo de tabla plano, bordes sutiles y cambio de fila interactivo con hover sutil.
Depth:      Bordes finos de 1px entre filas, sin sombras.
Surfaces:   Fondo base de superficie, con cabecera en superficie elevada.
Typography: Tickers y cifras en font-mono y tabular-nums (13px). Texto descriptivo en font-sans.
Spacing:    Padding horizontal de 12px (sp-3) y vertical de 8px (sp-2) en celdas para alta densidad.
```

```tsx
// components/ui/DenseTable.tsx
import React from 'react';
import { StatusBadge, BadgeType } from './StatusBadge';

export interface TableRowData {
  id: string;
  ticker: string;
  assetName: string;
  impact: 'positive' | 'negative' | 'neutral' | 'uncertain';
  price: string;
  change: string;
  changePercent: number;
  confidence: number; // 0.0 a 1.0
  source: string;
  date: string;
}

interface DenseTableProps {
  data: TableRowData[];
  onRowClick?: (row: TableRowData) => void;
}

export const DenseTable: React.FC<DenseTableProps> = ({ data, onRowClick }) => {
  return (
    <div className="w-full overflow-x-auto border border-border rounded-lg bg-surface">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b border-border bg-surface-elevated text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
            <th className="px-3 py-2 w-24">Activo</th>
            <th className="px-3 py-2 w-28">Impacto</th>
            <th className="px-3 py-2 text-right w-28">Precio</th>
            <th className="px-3 py-2 text-right w-24">Var. %</th>
            <th className="px-3 py-2 text-right w-24">Confianza</th>
            <th className="px-3 py-2">Fuente Primaria</th>
            <th className="px-3 py-2 text-right w-32">Fecha</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border text-[13px]">
          {data.map((row) => {
            const isPositive = row.changePercent > 0;
            const isNegative = row.changePercent < 0;
            
            return (
              <tr
                key={row.id}
                onClick={() => onRowClick && onRowClick(row)}
                className={`hover:bg-surface-elevated/50 transition-colors duration-100 ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
              >
                {/* Activo (Ticker) */}
                <td className="px-3 py-2 whitespace-nowrap">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-text-primary tracking-tight">
                      {row.ticker}
                    </span>
                    <span className="text-[11px] text-text-muted truncate max-w-[80px]">
                      {row.assetName}
                    </span>
                  </div>
                </td>
                {/* Impacto */}
                <td className="px-3 py-2 whitespace-nowrap">
                  <StatusBadge type={row.impact} />
                </td>
                {/* Precio */}
                <td className="px-3 py-2 text-right font-mono text-text-primary whitespace-nowrap tabular-nums">
                  {row.price}
                </td>
                {/* Var % */}
                <td 
                  className={`px-3 py-2 text-right font-mono font-medium whitespace-nowrap tabular-nums ${
                    isPositive ? 'text-status-positive-text' : isNegative ? 'text-status-negative-text' : 'text-text-secondary'
                  }`}
                >
                  {isPositive ? '+' : ''}{row.changePercent.toFixed(2)}%
                </td>
                {/* Confianza */}
                <td className="px-3 py-2 text-right font-mono text-text-primary whitespace-nowrap tabular-nums">
                  {(row.confidence * 100).toFixed(0)}%
                </td>
                {/* Fuente */}
                <td className="px-3 py-2 text-text-secondary truncate max-w-[150px]">
                  {row.source}
                </td>
                {/* Fecha */}
                <td className="px-3 py-2 text-right text-text-muted font-mono whitespace-nowrap">
                  {row.date}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
```

---

### 4.3 Tarjeta de Métrica Numérica (Metric Card)

Presenta métricas clave como el retorno del activo, volumen relativo o puntajes de volatilidad. Muestra visualmente las variaciones positivas o negativas.

```
Intent:     Un inversionista o analista evalúa la magnitud del movimiento del activo durante el evento.
Hierarchy:  El valor numérico central es el héroe indiscutible (24px, peso 600, tabular-nums). Las etiquetas secundarias se reducen para dar soporte.
Palette:    Los colores semánticos se limitan al indicador de tendencia y al texto de variación, manteniendo el resto en tonos grafito/plata.
Depth:      Contenedor plano con borde sutil. Sin sombras pesadas para encajar en el layout técnico.
Surfaces:   Superficie base de tarjeta.
Typography: Número en font-mono (24px, 600, tabular-nums). Etiquetas y variaciones en font-sans.
Spacing:    Padding simétrico de 16px (sp-4) para dar balance y espacio a la cifra heroica.
```

```tsx
// components/ui/MetricCard.tsx
import React from 'react';

interface MetricCardProps {
  label: string;
  value: string;
  changeLabel?: string;
  changeDirection?: 'up' | 'down' | 'flat';
  changeValue?: string;
  secondaryLabel?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  changeLabel,
  changeDirection = 'flat',
  changeValue,
  secondaryLabel,
}) => {
  const isUp = changeDirection === 'up';
  const isDown = changeDirection === 'down';

  return (
    <div className="border border-border rounded-lg bg-surface p-4 flex flex-col justify-between h-28 select-none">
      {/* Cabecera */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">
          {label}
        </span>
        {secondaryLabel && (
          <span className="text-[11px] font-mono text-text-muted">
            {secondaryLabel}
          </span>
        )}
      </div>

      {/* Valor Central */}
      <div className="my-1.5 flex items-baseline gap-2">
        <span className="text-2xl font-semibold font-mono tracking-tight text-text-primary tabular-nums">
          {value}
        </span>
      </div>

      {/* Pie de Métrica / Variación */}
      <div className="flex items-center gap-1.5 text-xs">
        {changeValue && (
          <span
            className={`font-mono font-semibold tabular-nums flex items-center ${
              isUp
                ? 'text-status-positive-text'
                : isDown
                ? 'text-status-negative-text'
                : 'text-text-secondary'
            }`}
          >
            {isUp ? '↑' : isDown ? '↓' : '•'} {changeValue}
          </span>
        )}
        {changeLabel && (
          <span className="text-[11px] text-text-muted truncate">
            {changeLabel}
          </span>
        )}
      </div>
    </div>
  );
};
```

---

### 4.4 Componente de Fuente y Fecha

Componente crucial para asegurar la trazabilidad y la procedencia de cada noticia o "claim" de información en la plataforma.

```
Intent:     Un analista de cumplimiento necesita conocer la procedencia exacta y la frescura de una noticia.
Hierarchy:  Componente de soporte (metadata). Es el rango más bajo de jerarquía en la vista (11px, regular, tono muted).
Palette:    Fondo sutil, texto en gris muted. Sin colores de acento para no distraer.
Depth:      Texto plano.
Surfaces:   Hereda la superficie sobre la que se sitúa.
Typography: font-sans de 11px con separadores claros (puntos medios) y partes de fecha técnica en font-mono.
Spacing:    Gap horizontal de 6px (sp-1.5) entre elementos.
```

```tsx
// components/ui/SourceDate.tsx
import React from 'react';

interface SourceDateProps {
  sourceName: string;
  sourceTier?: 'A' | 'B' | 'C' | 'D';
  publishedAt: string; // Ej: "10 jul 2026"
  relativeTime: string; // Ej: "hace 2h"
  isLiveData?: boolean;
}

export const SourceDate: React.FC<SourceDateProps> = ({
  sourceName,
  sourceTier,
  publishedAt,
  relativeTime,
  isLiveData = false,
}) => {
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-text-muted select-none">
      {/* Nombre de la Fuente */}
      <span className="font-semibold text-text-secondary">{sourceName}</span>

      {/* Tier (Calidad de la fuente) */}
      {sourceTier && (
        <span className="px-1 text-[9px] font-bold font-mono border border-border rounded-[2px] bg-surface-elevated/50 text-text-muted">
          TIER {sourceTier}
        </span>
      )}

      {/* Separador */}
      <span className="text-text-muted/60">•</span>

      {/* Fecha de Publicación */}
      <span className="font-mono">{publishedAt}</span>

      {/* Separador */}
      <span className="text-text-muted/60">•</span>

      {/* Tiempo Relativo */}
      <span>{relativeTime}</span>

      {/* Indicador de Origen / Datos en tiempo real vs Fixture */}
      {!isLiveData && (
        <>
          <span className="text-text-muted/60">•</span>
          <span className="px-1 text-[9px] font-semibold border border-status-uncertain-bg/50 rounded-[2px] bg-status-uncertain-bg/30 text-status-uncertain-text tracking-wide uppercase">
            Fixture Data
          </span>
        </>
      )}
    </div>
  );
};
```

---

## 5. Pruebas de Consistencia Visual y Verificación

### 5.1 Test del Squint (Squint Test)
Al desenfocar la vista sobre un panel que combine la `DenseTable`, `MetricCard` y `SourceDate`, se debe observar que:
1.  La cifra principal de la `MetricCard` y el código del activo (Ticker) de la `DenseTable` lideran la vista de manera inequívoca.
2.  Las líneas de división e interfaces estructurales (bordes) desaparecen y actúan únicamente como un contenedor secundario.
3.  Los badges de estado destacan en una tercera capa visual sin eclipsar el texto de datos.

### 5.2 Test del Swap (Swap Test)
Si se cambia la tipografía `Geist Mono` por una tipografía redondeada o de proporciones anchas de fantasía, las cifras numéricas perderán su alineación perfecta y la tabla empezará a vibrar al re-renderizar, demostrando la necesidad estricta de la escala tipográfica monoespaciada configurada para los números en NexoMercado AI.
