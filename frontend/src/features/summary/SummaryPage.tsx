import { ArrowRight } from 'lucide-react'
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useEventsQuery, useMarketSnapshotsQuery, useRecentRunsQuery, useSignalsQuery, useWatchlistQuery } from '../../shared/api/queries'
import { deriveMarketAssets } from '../../shared/api/mappers'
import { formatDateTime } from '../../shared/lib/format'
import { DataModeBadge } from '../../shared/ui/badges'
import { ErrorState, LoadingSkeleton, RefreshButton } from '../../shared/ui/primitives'
import { MarketAssetCard, MarketNewsSection, WatchlistPanel } from './components'
import { PrioritySignalsTable } from './PrioritySignalsTable'
import { ReviewMeter } from './ReviewMeter'

export function SummaryPage() {
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const marketSnapshotsQuery = useMarketSnapshotsQuery({ interval: '1d' })
  const watchlistQuery = useWatchlistQuery()
  const recentRunQueries = useRecentRunsQuery()
  const events = useMemo(() => eventsQuery.data?.items ?? [], [eventsQuery.data?.items])
  const signals = useMemo(() => signalsQuery.data?.items ?? [], [signalsQuery.data?.items])
  const snapshots = useMemo(() => marketSnapshotsQuery.data?.items ?? [], [marketSnapshotsQuery.data?.items])
  const assets = useMemo(() => deriveMarketAssets(snapshots, signals, events), [events, signals, snapshots])
  const recentRuns = recentRunQueries.map(item => item.data).filter((run): run is NonNullable<typeof run> => Boolean(run))
  const meta = marketSnapshotsQuery.data?.meta ?? signalsQuery.data?.meta ?? eventsQuery.data?.meta
  const isLoading = eventsQuery.isLoading || signalsQuery.isLoading || marketSnapshotsQuery.isLoading
  const hasError = eventsQuery.isError || signalsQuery.isError || marketSnapshotsQuery.isError
  const reviewedCount = signals.filter(signal => signal.reviewStatus === 'reviewed').length

  if (isLoading) return <LoadingSkeleton rows={10} />
  if (hasError) return (
    <ErrorState title="No se pudo cargar el panorama" description="El backend no devolvió todo el contexto. Reintenta sin sustituirlo por datos simulados." action={
      <RefreshButton label="Reintentar" busy={eventsQuery.isFetching || signalsQuery.isFetching || marketSnapshotsQuery.isFetching} onClick={() => {
        void eventsQuery.refetch(); void signalsQuery.refetch(); void marketSnapshotsQuery.refetch()
      }} />
    } />
  )

  return (
    <div className="page-stack panorama-page">
      <header className="page-heading">
        <div>
          <p className="section-eyebrow">01 · Panorama</p>
          <h1>Mercado, contexto y decisiones</h1>
          <p>Una vista compacta de los datos disponibles y del trabajo humano pendiente.</p>
        </div>
        <Link className="primary-button" to="/radar">Explorar radar <ArrowRight size={16} /></Link>
      </header>

      <div className="data-stamp">
        {meta ? <DataModeBadge mode={meta.dataMode} /> : null}
        <strong className="mono">{meta?.provider ?? 'backend'}</strong>
        <span>{meta?.warnings.length ? meta.warnings.join(' · ') : 'Información trazable'}</span>
        <span className="mono">corte {meta ? formatDateTime(meta.dataAsOf) : 'pendiente'}</span>
      </div>

      <section className="market-card-rail" aria-label="Activos de mercado">
        {assets.slice(0, 4).map(asset => <MarketAssetCard key={asset.assetId} asset={asset} />)}
      </section>

      <div className="panorama-grid">
        <div className="panorama-main">
          <PrioritySignalsTable signals={signals.toSorted((left, right) => right.confidence - left.confidence)} />
          <MarketNewsSection events={events.slice(0, 4)} signals={signals} />
        </div>
        <aside className="panorama-side">
          <ReviewMeter total={signals.length} reviewed={reviewedCount} />
          <WatchlistPanel watchlist={watchlistQuery.data} assets={assets} pendingCount={signals.length - reviewedCount} recentRuns={recentRuns} isLoading={watchlistQuery.isLoading || recentRunQueries.some(run => run.isLoading)} />
        </aside>
      </div>
    </div>
  )
}
