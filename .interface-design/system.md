# NexoMercado AI — Design System Specification

## 1. Direction and Feel
*   **Aesthetic Intent:** Serious, data-centric financial intelligence tool. NOT a generic AI product.
*   **Palette Philosophy:** Graphite base (`#121211`), Warm Charcoal (`#1A1A19`, `#242422`) surfaces, and Warm Bone/Parchment text (`#F5F4F0`). Accent colors: Copper/Rust (`#D95D39`) and Old Gold (`#C5A059`). No blue backgrounds or primary blue accents.
*   **Style Restrictions:** Flat, opaque containers with sharp technical borders. Zero gradients, zero rounded components.

## 2. Structural & Asymmetric Specs
*   **Spacing Base Unit:** 4px (All padding, margins, and gaps must align to multiples of 4px).
*   **Depth Strategy:** Borders-only. 1px thin borders with low opacity (`rgba(245, 244, 240, 0.08)`). No heavy drop shadows.
*   **Asymmetric Layout Guidelines:**
    *   **Featured Top-Story Card (Radar):** The first item of default streams must occupy a larger featured block (bold serif title, left accent bar, inline excerpt) to break identical list card repetition.
    *   **Printed Clippings Style (Briefing):** Summaries are formatted as asymmetric clippings with border-left highlights and an independent quick-stats sidebar panel.
    *   **Asymmetric Columns (SignalDetail):** Split columns are aligned 3:2 (`col-span-3` vs. `col-span-2`) to guide focal flow.
*   **Border Radius Scale:**
    *   `radius-sm` (1px): Badges, checkboxes, micro-inputs.
    *   `radius-md` (2px): Standard buttons, input fields, select elements.
    *   `radius-lg` (3px): Main panels, cards, dialog/modal overlays.

## 3. Typography & Hierarchy
*   **Typography Stack:**
    *   General Sans: `Inter`, `system-ui`, `-apple-system`, `sans-serif`
    *   Editorial Serif: `Newsreader`, Georgia, serif (Used for briefing summaries and news titles).
    *   Data/Numbers Mono: `Geist Mono`, `JetBrains Mono`, `monospace` (Mandatory `font-variant-numeric: tabular-nums` for all table values, prices, tickers, and percentages).
*   **Scale (Ratio ~1.2):**
    *   `caption-sm`: 10px / 500 / Mono (uppercase, tracking-wider)
    *   `caption`: 11px / 500 / Sans (uppercase, tracking-wide)
    *   `body-sm`: 13px / 400 / Sans
    *   `body`: 14px / 400 / Sans
    *   `h4`: 16px / 600 / Sans (tracking-tight)
    *   `h3`: 18px / 600 / Sans (tracking-tight)
    *   `h2`: 22px / 600 / Serif (tracking-tight)
    *   `h1`: 26px / 700 / Serif (tracking-tight)

## 4. Key Component Patterns

### `StatusBadge`
*   **Dimensions/Padding:** `2px` vertical, `6px` horizontal padding.
*   **Typography:** `10px` / `700` Mono, uppercase, tracking-wider.
*   **Radius:** `radius-sm` (1px).
*   **Design:** Border matching current text color with a tiny square indicator dot (`w-1.5 h-1.5`).

### `DenseTable`
*   **Structure:** Header row uses `--surface-elevated` background, cells have `text-[10px]` monospace uppercase.
*   **Cell Padding:** `6px` vertical, `12px` horizontal.
*   **Typography:** Tickers and prices are `13px` / `font-mono` / `tabular-nums` / semibold. General text is `13px` / `font-sans`.
*   **Row Interaction:** Subtle transition hover to `bg-surface-elevated/20`.

### `MetricCard`
*   **Dimensions:** Fixed height `28` (`112px`), padding `16px` (`sp-4`).
*   **Typography:** Value is `24px` / `700` / `font-mono` / `tabular-nums`. Labels are `10px` / `font-mono` uppercase.
*   **Layout:** Vertical flex column separating header, value, and footer change.

