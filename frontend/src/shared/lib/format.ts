export function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'Sin registro'
  return new Intl.DateTimeFormat('es-EC', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return 'Sin registro'
  const date = new Date(value)
  const diffMs = date.getTime() - Date.now()
  const rtf = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })
  const minutes = Math.round(diffMs / 60000)
  if (Math.abs(minutes) < 60) return rtf.format(minutes, 'minute')
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 24) return rtf.format(hours, 'hour')
  const days = Math.round(hours / 24)
  return rtf.format(days, 'day')
}

export function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return 'No disponible'
  return new Intl.NumberFormat('es-EC', {
    style: 'percent',
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
    signDisplay: 'always',
  }).format(value)
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return 'No disponible'
  return new Intl.NumberFormat('es-EC', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value)
}

export function formatCurrency(value: number | null | undefined, currency = 'USD'): string {
  if (value == null || Number.isNaN(value)) return 'No disponible'
  return new Intl.NumberFormat('es-EC', {
    style: 'currency',
    currency,
    maximumFractionDigits: value >= 1000 ? 0 : 2,
    minimumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value)
}

export function formatConfidence(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function compactId(value: string): string {
  if (value.length <= 18) return value
  return `${value.slice(0, 8)}...${value.slice(-6)}`
}

export function toSentenceCase(value: string): string {
  return value
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .replace(/\b\w/g, character => character.toUpperCase())
}
