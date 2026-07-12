import { Link } from 'react-router-dom'
import { useEventsQuery, useRecentRunsQuery, useSignalsQuery, useWatchlistQuery } from '../../shared/api/queries'
import { deriveAssetSummaries } from '../../shared/api/mappers'
import { SurfaceCard, LoadingSkeleton, EmptyState } from '../../shared/ui/primitives'
import { EventCard, MetricCard, RunCard, SignalCard } from '../../shared/ui/cards'
import { formatConfidence } from '../../shared/lib/format'

export function SummaryPage() {
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const watchlistQuery = useWatchlistQuery()
  const recentRuns = useRecentRunsQuery()
    .map(item => item.data)
    .filter((run): run is NonNullable<typeof run> => Boolean(run))

  if (eventsQuery.isLoading || signalsQuery.isLoading) {
    return <LoadingSkeleton rows={8} />
  }

  const events = eventsQuery.data?.items ?? []
  const signals = signalsQuery.data?.items ?? []
  const assets = deriveAssetSummaries(signals, events)
  const reviewedSignals = signals.filter(signal => signal.reviewStatus === 'reviewed')
  const pendingSignals = signals.filter(signal => signal.reviewStatus === 'pending_review')
  const topAsset = assets[0]
  const topSignal = signals.toSorted((left, right) => right.confidence - left.confidence)[0]

  return (
    <div className="page-stack">
      <section className="hero-grid">
        <SurfaceCard className="hero-panel" eyebrow="Resumen operativo" title="Panorama de mercado y trazabilidad">
          <p className="hero-copy">
            El panel prioriza explicabilidad, estado humano y frescura. Todo lo visible sale del backend actual o de derivaciones directas
            sobre contratos reales.
          </p>
          <div className="metric-grid">
            <MetricCard label="Eventos activos" value={String(events.length)} hint="Radar validado" />
            <MetricCard label="Senales abiertas" value={String(signals.length)} hint={`${pendingSignals.length} pendientes de revision`} />
            <MetricCard label="Senales revisadas" value={String(reviewedSignals.length)} hint="Aptas para briefing shareable" />
            <MetricCard label="Activo dominante" value={topAsset?.symbol ?? 'N/D'} hint={topAsset ? formatConfidence(topAsset.averageConfidence) : 'Sin datos'} />
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Watchlist" title="Cobertura demo-global">
          {watchlistQuery.data ? (
            <div className="compact-list">
              <div className="data-points">
                <span>{watchlistQuery.data.name}</span>
                <span>{watchlistQuery.data.assetIds.length} activos monitoreados</span>
              </div>
              {assets.slice(0, 4).map(asset => (
                <Link className="compact-row" key={asset.symbol} to={`/assets/${asset.symbol}`}>
                  <strong>{asset.symbol}</strong>
                  <span>{asset.signalCount} senales</span>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="Watchlist pendiente" description="La watchlist se hidrata una vez que radar y senales quedan disponibles." />
          )}
        </SurfaceCard>
      </section>

      <section className="content-grid">
        <SurfaceCard eyebrow="Prioridad" title="Senal con mayor conviccion">
          {topSignal ? <SignalCard signal={topSignal} /> : <EmptyState title="Sin senales" description="Aun no hay senales para destacar." />}
        </SurfaceCard>

        <SurfaceCard eyebrow="Recientes" title="Runs de analisis">
          {recentRuns.length ? recentRuns.slice(0, 3).map(run => <RunCard key={run.id} run={run} />) : <EmptyState title="Sin runs recientes" description="Lanza un analisis desde la barra superior para poblar la auditoria." />}
        </SurfaceCard>
      </section>

      <section className="content-grid">
        <SurfaceCard eyebrow="Radar" title="Eventos recientes">
          <div className="stack-list">
            {events.slice(0, 4).map(event => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Activos" title="Activos con mayor actividad">
          <div className="stack-list">
            {assets.slice(0, 4).map(asset => (
              <article key={asset.symbol} className="list-card">
                <div className="list-card__header">
                  <div>
                    <p className="section-eyebrow">{asset.instrumentType}</p>
                    <h3>{asset.symbol}</h3>
                  </div>
                  <span className="muted-pill">{formatConfidence(asset.averageConfidence)}</span>
                </div>
                <p>{asset.name}</p>
                <div className="data-points">
                  <span>{asset.signalCount} senales</span>
                  <span>{asset.eventCount} eventos</span>
                </div>
                <div className="card-actions">
                  <Link className="text-link" to={`/assets/${asset.symbol}`}>
                    Abrir activo
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </SurfaceCard>
      </section>
    </div>
  )
}
