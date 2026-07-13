import { useParams } from 'react-router-dom'
import { useEventsQuery, useInstrumentsQuery, useMarketQuotesQuery, useMarketSnapshotsQuery, useSignalsQuery } from '../../shared/api/queries'
import { formatCurrency, formatPercent } from '../../shared/lib/format'
import { DataModeBadge } from '../../shared/ui/badges'
import { deriveAssetSummaries } from '../../shared/api/mappers'
import { ReactionChart } from '../../shared/ui/charts/ReactionChart'
import { BackToHomeButton, EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { SignalCard } from '../../shared/ui/cards'

export function AssetDetailPage() {
  const { symbol = '' } = useParams()
  const eventsQuery = useEventsQuery({ asset: symbol })
  const signalsQuery = useSignalsQuery()
  const snapshotsQuery = useMarketSnapshotsQuery({ asset: symbol, interval: '1d' }, { enabled: Boolean(symbol) })
  const instrumentsQuery = useInstrumentsQuery(symbol)
  const quoteQuery = useMarketQuotesQuery(symbol ? [symbol.toUpperCase()] : [], { enabled: Boolean(symbol) })
  const events = eventsQuery.data?.items ?? []
  const matchingSignals = (signalsQuery.data?.items ?? []).filter(item => item.asset.symbol.toLowerCase() === symbol.toLowerCase())
  const asset = deriveAssetSummaries(matchingSignals, events)[0] ?? null
  const instrument = instrumentsQuery.data?.items.find(item => item.symbol.toLowerCase() === symbol.toLowerCase()) ?? null
  const quote = quoteQuery.data?.items[0] ?? null

  if (eventsQuery.isLoading || signalsQuery.isLoading || snapshotsQuery.isLoading || instrumentsQuery.isLoading) return <LoadingSkeleton rows={10} />
  if (!instrument) {
    return (
      <EmptyState
        title="Activo no disponible"
        description="El símbolo no pertenece al universo productivo configurado."
      />
    )
  }

  return (
    <div className="page-stack">
      <BackToHomeButton />
      <SurfaceCard eyebrow={instrument.instrumentType} title={`${instrument.symbol} · ${instrument.name}`}>
        <p className="hero-copy">
          Cotización consultada por FastAPI con procedencia auditable. Las señales aparecen únicamente cuando existe análisis y revisión.
        </p>
        <div className="data-stamp">
          {quote ? <DataModeBadge mode={quote.dataMode} /> : null}
          <strong>{formatCurrency(quote?.price ?? null, instrument.currency)}</strong>
          <span>{quote?.changePercent == null ? 'Cambio no disponible' : formatPercent(quote.changePercent)}</span>
          <span>{quote?.provider ?? instrument.exchange}</span>
        </div>
        <div className="metric-grid">
          <article className="metric-card">
            <span>Señales</span>
            <strong>{asset?.signalCount ?? 0}</strong>
          </article>
          <article className="metric-card">
            <span>Eventos</span>
            <strong>{asset?.eventCount ?? 0}</strong>
          </article>
          <article className="metric-card">
            <span>Confianza media</span>
            <strong>{asset ? Math.round(asset.averageConfidence * 100) : 0}%</strong>
          </article>
        </div>
      </SurfaceCard>

      {asset?.latestSignal ? <ReactionChart signal={asset.latestSignal} snapshot={snapshotsQuery.data?.items[0] ?? null} /> : null}

      <SurfaceCard eyebrow="Limitaciones honestas" title="Cobertura del endpoint actual">
        <ul className="text-list">
          <li>El endpoint actual expone snapshots verificables, no series profundas ilimitadas.</li>
          <li>No hay order book ni fundamentals detallados dentro del contrato actual.</li>
          <li>La trazabilidad visible se construye a partir de señales y eventos confirmados por backend.</li>
        </ul>
      </SurfaceCard>

      <SurfaceCard eyebrow="Señales del activo" title="Contexto actual">
        <div className="stack-list">
          {(asset?.signals ?? []).map(signal => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      </SurfaceCard>
    </div>
  )
}
