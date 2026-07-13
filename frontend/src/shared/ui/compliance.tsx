import type { SignalViewModel } from '../types/view-models'
import { formatNumber, formatPercent } from '../lib/format'
import { MetricCard } from './cards'

export const SIGNAL_DISCLAIMER =
  'Esta señal es informativa, no constituye asesoría financiera personalizada ni garantiza resultados.'

export function SignalDisclaimer({ text }: { text?: string }) {
  return (
    <p className="signal-disclaimer" role="note">
      {text ?? SIGNAL_DISCLAIMER}
    </p>
  )
}

export function PriceReactionMetrics({ signal }: { signal: SignalViewModel }) {
  if (!signal.priceReactionRows.length) {
    return <p className="signal-disclaimer">Sin reacción de precio verificable para esta señal.</p>
  }

  return (
    <div className="price-reaction-grid">
      {signal.priceReactionRows.map(row => (
        <MetricCard
          key={row.key}
          label={row.label}
          value={row.key === 'relativeVolume' ? `${formatNumber(row.value, 2)}x` : formatPercent(row.value)}
        />
      ))}
    </div>
  )
}
