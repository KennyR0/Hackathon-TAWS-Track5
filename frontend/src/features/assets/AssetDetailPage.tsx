import { useParams } from 'react-router-dom'
import { useEventsQuery, useMarketSnapshotsQuery, useSignalsQuery } from '../../shared/api/queries'
import { deriveAssetSummaries } from '../../shared/api/mappers'
import { ReactionChart } from '../../shared/ui/charts/ReactionChart'
import { BackToHomeButton, EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { SignalCard } from '../../shared/ui/cards'

export function AssetDetailPage() {
  const { symbol = '' } = useParams()
  const eventsQuery = useEventsQuery({ asset: symbol })
  const signalsQuery = useSignalsQuery()
  const snapshotsQuery = useMarketSnapshotsQuery({ asset: symbol, interval: '1d' }, { enabled: Boolean(symbol) })
  const events = eventsQuery.data?.items ?? []
  const matchingSignals = (signalsQuery.data?.items ?? []).filter(item => item.asset.symbol.toLowerCase() === symbol.toLowerCase())
  const asset = deriveAssetSummaries(matchingSignals, events)[0] ?? null

  if (eventsQuery.isLoading || signalsQuery.isLoading || snapshotsQuery.isLoading) return <LoadingSkeleton rows={10} />
  if (!asset) {
    return (
      <EmptyState
        title="Activo no disponible"
        description="El backend actual no expone un endpoint profundo por activo. Esta vista depende de señales y eventos ya vinculados."
      />
    )
  }

  return (
    <div className="page-stack">
      <BackToHomeButton />
      <SurfaceCard eyebrow={asset.instrumentType} title={`${asset.symbol} · ${asset.name}`}>
        <p className="hero-copy">
          Esta vista se deriva de señales, eventos y snapshots embebidos en respuestas existentes. Cuando el backend exponga series históricas
          dedicadas, aqui podremos ampliar profundidad sin cambiar la ruta.
        </p>
        <div className="metric-grid">
          <article className="metric-card">
            <span>Señales</span>
            <strong>{asset.signalCount}</strong>
          </article>
          <article className="metric-card">
            <span>Eventos</span>
            <strong>{asset.eventCount}</strong>
          </article>
          <article className="metric-card">
            <span>Confianza media</span>
            <strong>{Math.round(asset.averageConfidence * 100)}%</strong>
          </article>
        </div>
      </SurfaceCard>

      {asset.latestSignal ? <ReactionChart signal={asset.latestSignal} snapshot={snapshotsQuery.data?.items[0] ?? null} /> : null}

      <SurfaceCard eyebrow="Limitaciones honestas" title="Cobertura del endpoint actual">
        <ul className="text-list">
          <li>El endpoint actual expone snapshots verificables, no series profundas ilimitadas.</li>
          <li>No hay order book ni fundamentals detallados dentro del contrato actual.</li>
          <li>La trazabilidad visible se construye a partir de señales y eventos confirmados por backend.</li>
        </ul>
      </SurfaceCard>

      <SurfaceCard eyebrow="Señales del activo" title="Contexto actual">
        <div className="stack-list">
          {asset.signals.map(signal => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      </SurfaceCard>
    </div>
  )
}
