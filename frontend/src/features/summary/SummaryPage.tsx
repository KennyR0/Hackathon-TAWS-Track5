import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useCreateAnalysisMutation,
  useEventsQuery,
  useMarketSnapshotsQuery,
  useRecentRunsQuery,
  useSignalsQuery,
  useWatchlistQuery,
} from '../../shared/api/queries'
import { deriveMarketAssets } from '../../shared/api/mappers'
import { ErrorState, LoadingSkeleton, RefreshButton } from '../../shared/ui/primitives'
import {
  MarketAssetCard,
  MarketNewsSection,
  MarketOverview,
  MarketTabs,
  PrioritySignalCard,
  WatchlistPanel,
} from './components'
import { buildMarketCategories, filterAssetsByCategory } from './market-helpers'

export function SummaryPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const marketSnapshotsQuery = useMarketSnapshotsQuery({ interval: '1d' })
  const watchlistQuery = useWatchlistQuery()
  const recentRunQueries = useRecentRunsQuery()
  const recentRuns = recentRunQueries
    .map(item => item.data)
    .filter((run): run is NonNullable<typeof run> => Boolean(run))
  const createAnalysis = useCreateAnalysisMutation()

  const eventsData = eventsQuery.data?.items
  const signalsData = signalsQuery.data?.items
  const snapshotsData = marketSnapshotsQuery.data?.items
  const events = useMemo(() => eventsData ?? [], [eventsData])
  const signals = useMemo(() => signalsData ?? [], [signalsData])
  const snapshots = useMemo(() => snapshotsData ?? [], [snapshotsData])
  const assets = useMemo(() => deriveMarketAssets(snapshots, signals, events), [snapshots, signals, events])
  const categories = useMemo(() => buildMarketCategories(assets), [assets])
  const firstEnabledCategory = categories.find(category => category.enabled)?.id ?? 'us'
  const [activeCategory, setActiveCategory] = useState(firstEnabledCategory)
  const selectedCategory = categories.some(category => category.id === activeCategory && category.enabled) ? activeCategory : firstEnabledCategory
  const visibleAssets = filterAssetsByCategory(assets, selectedCategory)
  const topSignal = signals.toSorted((left, right) => right.confidence - left.confidence)[0] ?? null
  const pendingCount = signals.filter(signal => signal.reviewStatus === 'pending_review').length
  const meta = marketSnapshotsQuery.data?.meta ?? signalsQuery.data?.meta ?? eventsQuery.data?.meta
  const isLoading = eventsQuery.isLoading || signalsQuery.isLoading || marketSnapshotsQuery.isLoading
  const hasError = eventsQuery.isError || signalsQuery.isError || marketSnapshotsQuery.isError

  const handleSearch = () => {
    const trimmed = query.trim()
    if (!trimmed) return
    const signal = signals.find(
      item =>
        item.id.toLowerCase() === trimmed.toLowerCase() ||
        item.asset.symbol.toLowerCase() === trimmed.toLowerCase() ||
        item.asset.name.toLowerCase().includes(trimmed.toLowerCase()),
    )
    if (signal) {
      navigate(`/signals/${signal.id}`)
      return
    }
    navigate(`/radar?asset=${encodeURIComponent(trimmed.toUpperCase())}`)
  }

  const handleAnalyze = async () => {
    const candidate = events.find(event => event.relatedAssets.length > 0)
    if (!candidate) return
    const response = await createAnalysis.mutateAsync({
      eventId: candidate.id,
      assetIds: candidate.relatedAssets.map(asset => asset.assetId),
    })
    navigate(`/audit/${response.data.id}`)
  }

  if (isLoading) return <LoadingSkeleton rows={10} />

  if (hasError) {
    return (
      <ErrorState
        title="No se pudo cargar el panorama"
        description="Alguna consulta del backend fallo. Puedes reintentar sin sustituir los datos por valores inventados."
        action={
          <RefreshButton
            label="Reintentar"
            busy={eventsQuery.isFetching || signalsQuery.isFetching || marketSnapshotsQuery.isFetching}
            onClick={() => {
              void eventsQuery.refetch()
              void signalsQuery.refetch()
              void marketSnapshotsQuery.refetch()
            }}
          />
        }
      />
    )
  }

  return (
    <div className="market-page">
      <MarketOverview
        meta={meta}
        query={query}
        onQueryChange={setQuery}
        onSearch={handleSearch}
        onAnalyze={() => {
          void handleAnalyze()
        }}
        isAnalyzing={createAnalysis.isPending}
        canAnalyze={events.length > 0}
      />

      <MarketTabs categories={categories} activeCategory={selectedCategory} onChange={setActiveCategory} />

      <section className="market-layout">
        <div className="market-main-column">
          <section className="market-section" aria-label="Tarjetas de mercado">
            <div className="market-card-rail">
              {visibleAssets.length ? (
                visibleAssets.map(asset => <MarketAssetCard key={asset.assetId} asset={asset} />)
              ) : (
                <ErrorState title="Mercado sin datos" description="Esta categoria no tiene activos verificables en el backend actual." />
              )}
            </div>
          </section>

          <PrioritySignalCard signal={topSignal} />

          <MarketNewsSection events={events} signals={signals} />
        </div>

        <WatchlistPanel
          watchlist={watchlistQuery.data}
          assets={assets}
          pendingCount={pendingCount}
          recentRuns={recentRuns}
          isLoading={watchlistQuery.isLoading || recentRunQueries.some(run => run.isLoading)}
        />
      </section>
    </div>
  )
}
