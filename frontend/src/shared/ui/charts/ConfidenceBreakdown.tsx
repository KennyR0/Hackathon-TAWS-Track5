import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SignalViewModel } from '../../types/view-models'
import { formatConfidence, formatNumber } from '../../lib/format'

const colors = ['#2dd4bf', '#60a5fa', '#f59e0b', '#f97316']

export function ConfidenceBreakdown({ signal }: { signal: SignalViewModel }) {
  const rows = [
    { name: 'Confianza', value: signal.confidence * 100 },
    { name: 'Evidencia', value: signal.evidenceIds.length * 10 },
    { name: 'Contra', value: signal.counterEvidenceIds.length * 10 },
    { name: 'Alertas', value: signal.meta.warnings.length * 10 },
  ]

  return (
    <div className="chart-panel">
      <div className="chart-panel__header">
        <h3>Desglose de confianza</h3>
        <span>{formatConfidence(signal.confidence)}</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={rows}>
          <CartesianGrid stroke="rgba(148, 163, 184, 0.12)" vertical={false} />
          <XAxis dataKey="name" stroke="#8f9bb3" tickLine={false} axisLine={false} />
          <YAxis stroke="#8f9bb3" tickLine={false} axisLine={false} />
          <Tooltip
            cursor={{ fill: 'rgba(148, 163, 184, 0.08)' }}
            formatter={value => `${formatNumber(Number(value), 0)} pts`}
            contentStyle={{ background: '#111827', borderRadius: 12, border: '1px solid rgba(148,163,184,0.15)' }}
          />
          <Bar dataKey="value" radius={[8, 8, 0, 0]}>
            {rows.map((entry, index) => (
              <Cell key={entry.name} fill={colors[index % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="chart-caption">Las barras mezclan confianza reportada, cobertura de evidencia y ruido operativo visible en el contrato.</p>
    </div>
  )
}
