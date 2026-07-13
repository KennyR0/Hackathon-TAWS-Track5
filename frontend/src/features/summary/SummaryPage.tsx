import { ArrowRight } from 'lucide-react'
import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useEventsQuery, useMarketSnapshotsQuery, useProviderRuntimeQuery, useRecentRunsQuery, useSignalsQuery, useWatchlistQuery } from '../../shared/api/queries'
import { deriveMarketAssets } from '../../shared/api/mappers'
import type { MarketAssetViewModel } from '../../shared/types/view-models'
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
  const providerRuntimeQuery = useProviderRuntimeQuery({ enabled: true })
  const watchlistQuery = useWatchlistQuery()
  const recentRunQueries = useRecentRunsQuery()
  const events = useMemo(() => eventsQuery.data?.items ?? [], [eventsQuery.data?.items])
  const signals = useMemo(() => signalsQuery.data?.items ?? [], [signalsQuery.data?.items])
  const snapshots = useMemo(() => marketSnapshotsQuery.data?.items ?? [], [marketSnapshotsQuery.data?.items])
  const assets = useMemo(
    () => applyLiveProviderPrices(deriveMarketAssets(snapshots, signals, events), providerRuntimeQuery.data?.status.checks ?? []),
    [events, providerRuntimeQuery.data?.status.checks, signals, snapshots],
  )
  const recentRuns = recentRunQueries.map(item => item.data).filter((run): run is NonNullable<typeof run> => Boolean(run))
  const meta = providerRuntimeQuery.data?.meta ?? marketSnapshotsQuery.data?.meta ?? signalsQuery.data?.meta ?? eventsQuery.data?.meta
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

function applyLiveProviderPrices(
  assets: MarketAssetViewModel[],
  checks: NonNullable<ReturnType<typeof useProviderRuntimeQuery>['data']>['status']['checks'],
): MarketAssetViewModel[] {
  const priceBySymbol = new Map<string, { current: number; previous: number | null }>()

  for (const check of checks) {
    if (check.dataMode !== 'live') continue
    const symbol = check.key === 'btc' ? 'BTC-USD' : check.key === 'wti' ? 'WTI' : check.key.toUpperCase()
    const rawCurrent = check.key === 'aapl' ? check.metrics.close : check.key === 'spy' ? check.metrics.current : check.key === 'btc' ? check.metrics.usd : check.metrics.value
    const current = typeof rawCurrent === 'string' ? Number(rawCurrent) : rawCurrent
    if (typeof current !== 'number' || !Number.isFinite(current)) continue
    const rawPrevious = check.key === 'spy' ? check.metrics.previousClose : null
    const previous = typeof rawPrevious === 'number' && Number.isFinite(rawPrevious) ? rawPrevious : null
    priceBySymbol.set(symbol, { current, previous })
  }

  return assets.map(asset => {
    const live = priceBySymbol.get(asset.symbol)
    if (!live) return asset
    const changeAbsolute = live.previous == null ? null : live.current - live.previous
    const changePercent = live.previous == null || live.previous === 0 ? null : changeAbsolute! / live.previous
    return {
      ...asset,
      price: live.current,
      changeAbsolute,
      changePercent,
      status: changeAbsolute == null ? asset.status : changeAbsolute > 0 ? 'positive' : changeAbsolute < 0 ? 'negative' : 'neutral',
    }
  })
}
