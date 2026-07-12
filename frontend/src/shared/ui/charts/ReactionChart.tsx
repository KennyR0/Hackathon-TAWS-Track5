import { createChart, LineSeries } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { SignalViewModel } from '../../types/view-models'
import { formatPercent } from '../../lib/format'

export function ReactionChart({ signal }: { signal: SignalViewModel }) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!containerRef.current || !signal.priceReaction) return

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
    assetSeries.setData([
      { time: '2026-07-09', value: 100 },
      { time: '2026-07-10', value: 100 * (1 + signal.priceReaction.assetReturn) },
    ])

    if (signal.priceReaction.benchmarkReturn != null) {
      const benchmarkSeries = chart.addSeries(LineSeries, { color: '#60a5fa', lineWidth: 2 })
      benchmarkSeries.setData([
        { time: '2026-07-09', value: 100 },
        { time: '2026-07-10', value: 100 * (1 + signal.priceReaction.benchmarkReturn) },
      ])
    }

    return () => chart.remove()
  }, [signal])

  if (!signal.priceReaction) {
    return <p className="chart-caption">La API actual no expone snapshots temporales suficientes para trazar una reaccion historica completa.</p>
  }

  return (
    <div className="chart-panel">
      <div className="chart-panel__header">
        <h3>Reaccion normalizada del activo</h3>
        <span>{formatPercent(signal.priceReaction.assetReturn)}</span>
      </div>
      <div className="lightweight-chart" ref={containerRef} />
      <p className="chart-caption">Serie derivada de la reaccion reportada por backend. No sustituye un historial OHLC completo.</p>
    </div>
  )
}
