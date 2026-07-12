import { Link } from 'react-router-dom'
import { Area, AreaChart, ResponsiveContainer, Tooltip } from 'recharts'
import { ArrowUpRight, Search, Sparkles } from 'lucide-react'
import type {
  DataMetaViewModel,
  EventViewModel,
  MarketAssetViewModel,
  MarketSnapshotViewModel,
  RunViewModel,
  SignalViewModel,
  WatchlistViewModel,
} from '../../shared/types/view-models'
import { formatConfidence, formatCurrency, formatDateTime, formatPercent, formatRelativeTime } from '../../shared/lib/format'
import { DataFreshnessIndicator, DataModeBadge, ImpactBadge, ReviewStatusBadge } from '../../shared/ui/badges'
import { EmptyState, LoadingSkeleton } from '../../shared/ui/primitives'
import { RunCard } from '../../shared/ui/cards'

export interface MarketCategory {
  id: string
  label: string
  enabled: boolean
  assetCount: number
}

export function MarketOverview({
  meta,
  query,
  onQueryChange,
  onSearch,
  onAnalyze,
  isAnalyzing,
  canAnalyze,
}: {
  meta?: DataMetaViewModel
  query: string
  onQueryChange: (value: string) => void
  onSearch: () => void
  onAnalyze: () => void
  isAnalyzing: boolean
  canAnalyze: boolean
}) {
  return (
    <section className="market-hero" aria-labelledby="market-overview-title">
      <div className="market-hero__copy">
        <p className="section-eyebrow">Resumen</p>
        <h1 id="market-overview-title">Panorama del mercado</h1>
        <p>
          Información construida desde señales, eventos y datos verificables del backend. No hay datos inventados ni
          proveedores llamados desde React.
        </p>
        <div className="market-hero__meta">
          {meta ? <DataModeBadge mode={meta.dataMode} /> : null}
          {meta ? <DataFreshnessIndicator asOf={meta.dataAsOf} retrievedAt={meta.retrievedAt} /> : null}
          {meta ? <span>Datos al {formatDateTime(meta.dataAsOf)}</span> : <span>Actualizacion pendiente</span>}
        </div>
      </div>

      <div className="market-hero__actions">
        <form
          className="market-search"
          onSubmit={event => {
            event.preventDefault()
            onSearch()
          }}
        >
          <Search size={16} aria-hidden="true" />
          <input
            aria-label="Buscar símbolo, activo o señal"
            value={query}
            onChange={event => onQueryChange(event.target.value)}
            placeholder="Buscar AAPL, BTC-USD o signalId"
          />
          <button className="icon-button" type="submit" aria-label="Buscar">
            <ArrowUpRight size={16} />
          </button>
        </form>
        <button className="primary-button market-hero__button" type="button" onClick={onAnalyze} disabled={isAnalyzing || !canAnalyze}>
          <Sparkles size={16} />
          {isAnalyzing ? 'Lanzando análisis' : 'Nuevo análisis'}
        </button>
      </div>
    </section>
  )
}

export function MarketTabs({
  categories,
  activeCategory,
  onChange,
}: {
  categories: MarketCategory[]
  activeCategory: string
  onChange: (categoryId: string) => void
}) {
  return (
    <div className="market-tabs" role="tablist" aria-label="Mercados">
      {categories.map(category => (
        <button
          key={category.id}
          type="button"
          role="tab"
          aria-selected={activeCategory === category.id}
          className={activeCategory === category.id ? 'market-tab market-tab--active' : 'market-tab'}
          onClick={() => {
            if (category.enabled) onChange(category.id)
          }}
          disabled={!category.enabled}
        >
          <span>{category.label}</span>
          <small>{category.enabled ? `${category.assetCount} activos` : 'Proximamente'}</small>
        </button>
      ))}
    </div>
  )
}

export function MarketAssetCard({ asset }: { asset: MarketAssetViewModel }) {
  const content = (
    <>
      <div className="market-card__header">
        <div>
          <span className="section-eyebrow">{asset.instrumentType}</span>
          <h3>{asset.symbol}</h3>
          <p>{asset.name}</p>
        </div>
        <ImpactBadge impact={asset.status} />
      </div>
      <div className="market-card__price">
        <strong>{formatCurrency(asset.price, asset.currency)}</strong>
        <span className={asset.changeAbsolute == null ? 'market-change' : asset.changeAbsolute >= 0 ? 'market-change market-change--up' : 'market-change market-change--down'}>
          {asset.changeAbsolute == null ? 'Sin cambio' : `${formatCurrency(asset.changeAbsolute, asset.currency)} (${formatPercent(asset.changePercent)})`}
        </span>
      </div>
      <MarketSparkline snapshot={asset.snapshot} status={asset.status} />
      <div className="market-card__footer">
        <span>{asset.snapshot ? `Actualizado ${formatRelativeTime(asset.snapshot.retrievedAt)}` : 'Sin historial real'}</span>
        {asset.latestSignal ? <span>Abrir señal</span> : <span>Sin señal disponible</span>}
      </div>
    </>
  )

  if (!asset.latestSignal) {
    return (
      <article className="market-card market-card--disabled" aria-label={`${asset.symbol}: sin señal disponible`}>
        {content}
      </article>
    )
  }

  return (
    <Link className="market-card market-card--interactive" to={`/signals/${asset.latestSignal.id}`} aria-label={`Abrir señal de ${asset.symbol}`}>
      {content}
    </Link>
  )
}

export function MarketSparkline({
  snapshot,
  status,
}: {
  snapshot: MarketSnapshotViewModel | null
  status: SignalViewModel['impact']
}) {
  if (!snapshot || snapshot.observations.length < 2) {
    return <div className="market-sparkline market-sparkline--empty">Sin historial verificable</div>
  }

  const color = status === 'negative' ? '#fb7185' : status === 'positive' ? '#34d399' : '#60a5fa'
  const data = snapshot.observations.map(point => ({
    timestamp: point.timestamp,
    value: point.close,
  }))

  return (
    <div className="market-sparkline" aria-label={`Historial verificable de ${snapshot.assetId}`}>
      <ResponsiveContainer width="100%" height={72}>
        <AreaChart data={data} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
          <Tooltip
            cursor={{ stroke: 'rgba(148, 163, 184, 0.24)' }}
            contentStyle={{ background: '#101826', border: '1px solid rgba(148, 163, 184, 0.24)', borderRadius: 10 }}
            labelFormatter={value => formatDateTime(String(value))}
            formatter={value => [formatCurrency(typeof value === 'number' ? value : Number(value), snapshot.currency), 'Cierre']}
          />
          <Area type="monotone" dataKey="value" stroke={color} fill={color} fillOpacity={0.12} strokeWidth={2} isAnimationActive={false} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function MarketNewsSection({
  events,
  signals,
}: {
  events: EventViewModel[]
  signals: SignalViewModel[]
}) {
  if (!events.length) {
    return <EmptyState title="Sin noticias disponibles" description="El radar no devolvio eventos para mostrar en el resumen." />
  }

  return (
    <section className="market-section" aria-labelledby="market-news-title">
      <div className="market-section__header">
        <div>
          <p className="section-eyebrow">Radar</p>
          <h2 id="market-news-title">Noticias y eventos relevantes</h2>
        </div>
      </div>
      <div className="market-news-list">
        {events.map(event => {
          const signal = signals.find(item => item.eventId === event.id) ?? null
          const source = event.sources.find(item => item.id === event.mainArticle?.sourceId) ?? event.sources[0]
          return <MarketNewsCard key={event.id} event={event} signal={signal} sourceName={source?.name ?? 'Fuente no disponible'} />
        })}
      </div>
    </section>
  )
}

function MarketNewsCard({
  event,
  signal,
  sourceName,
}: {
  event: EventViewModel
  signal: SignalViewModel | null
  sourceName: string
}) {
  return (
    <article className="market-news-card">
      <div className="market-news-card__body">
        <div className="market-news-card__meta">
          <span>{sourceName}</span>
          <span>{formatDateTime(event.mainArticle?.publishedAt ?? event.eventAt)}</span>
          <span>{event.independentSourceCount} fuentes independientes</span>
        </div>
        <h3>{event.title}</h3>
        <p>{event.summary}</p>
        <div className="badge-row">
          {event.relatedAssets.map(asset => (
            <span className="muted-pill" key={`${event.id}-${asset.assetId}`}>
              {asset.symbol}
            </span>
          ))}
          {signal ? <ImpactBadge impact={signal.impact} /> : null}
          {signal ? <ReviewStatusBadge status={signal.reviewStatus} /> : null}
        </div>
      </div>
      <div className="market-news-card__aside">
        {signal ? (
          <>
            <strong>{formatConfidence(signal.confidence)}</strong>
            <span>confianza</span>
            <Link className="text-link" to={`/signals/${signal.id}`}>
              Ver señal
            </Link>
          </>
        ) : (
          <span>Sin señal asociada</span>
        )}
      </div>
    </article>
  )
}

export function WatchlistPanel({
  watchlist,
  assets,
  pendingCount,
  recentRuns,
  isLoading,
}: {
  watchlist?: WatchlistViewModel
  assets: MarketAssetViewModel[]
  pendingCount: number
  recentRuns: RunViewModel[]
  isLoading: boolean
}) {
  if (isLoading) return <LoadingSkeleton rows={6} />

  return (
    <aside className="market-side-panel" aria-label="Watchlist y actividad">
      <section className="market-side-card">
        <p className="section-eyebrow">Watchlist</p>
        <h2>{watchlist?.name ?? 'Demo Global'}</h2>
        <div className="watchlist-rows">
          {assets.slice(0, 5).map(asset => (
            <Link key={asset.assetId} className="watchlist-row" to={asset.latestSignal ? `/signals/${asset.latestSignal.id}` : `/assets/${asset.symbol}`}>
              <span>{asset.symbol}</span>
              <strong>{asset.signalCount} señales</strong>
            </Link>
          ))}
        </div>
      </section>
      <section className="market-side-card">
        <p className="section-eyebrow">Revisión</p>
        <h2>{pendingCount} pendientes</h2>
        <Link className="text-link" to="/reviews">
          Abrir cola
        </Link>
      </section>
      <section className="market-side-card">
        <p className="section-eyebrow">Runs recientes</p>
        <div className="stack-list">
          {recentRuns.length ? recentRuns.slice(0, 2).map(run => <RunCard key={run.id} run={run} />) : <p>Sin ejecuciones recientes.</p>}
        </div>
      </section>
    </aside>
  )
}

export function PrioritySignalCard({ signal }: { signal: SignalViewModel | null }) {
  if (!signal) {
    return <EmptyState title="Sin señal destacada" description="Cuando exista una señal con confianza disponible aparecerá aquí." />
  }

  return (
    <article className="priority-signal-card">
      <div>
        <p className="section-eyebrow">Señal destacada</p>
        <h2>{signal.asset.symbol}</h2>
        <p>{signal.thesis ?? 'Tesis pendiente de sintesis.'}</p>
      </div>
      <div className="priority-signal-card__meta">
        <ImpactBadge impact={signal.impact} />
        <ReviewStatusBadge status={signal.reviewStatus} />
        <span>{formatConfidence(signal.confidence)}</span>
      </div>
      <Link className="text-link" to={`/signals/${signal.id}`}>
        Abrir señal
      </Link>
    </article>
  )
}
