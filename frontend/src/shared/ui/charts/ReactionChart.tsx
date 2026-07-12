import { createChart, LineSeries } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { MarketSnapshotViewModel, SignalViewModel } from '../../types/view-models'
import { formatDateTime, formatPercent } from '../../lib/format'

export function ReactionChart({ signal, snapshot }: { signal: SignalViewModel; snapshot?: MarketSnapshotViewModel | null }) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current || !snapshot || snapshot.observations.length < 2) return

    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { color: 'transparent' }, textColor: '#9ca3af' },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.08)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.08)' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      crosshair: { vertLine: { labelVisible: false }, horzLine: { labelVisible: false } },
    })

    const assetSeries = chart.addSeries(LineSeries, { color: '#22c55e', lineWidth: 2 })
    assetSeries.setData(snapshot.observations.map(point => ({ time: point.timestamp.slice(0, 10), value: point.close })))

    return () => chart.remove()
  }, [snapshot])

  if (!snapshot || snapshot.observations.length < 2) {
    return <p className="chart-caption">La API actual no expone un historial verificable suficiente para este activo.</p>
  }

  return (
    <div className="chart-panel">
      <div className="chart-panel__header">
        <h3>Historial verificable del activo</h3>
        <span>{signal.priceReaction ? formatPercent(signal.priceReaction.assetReturn) : 'Sin reaccion'}</span>
      </div>
      <div className="lightweight-chart" ref={containerRef} />
      <p className="chart-caption">
        Observaciones reales del snapshot {snapshot.id}. Datos al {formatDateTime(snapshot.dataAsOf)}.
      </p>
    </div>
  )
}
