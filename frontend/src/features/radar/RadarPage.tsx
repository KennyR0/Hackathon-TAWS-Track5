import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { useEventQuery, useEventsQuery } from '../../shared/api/queries'
import { useStartAnalysis } from '../../shared/api/useStartAnalysis'
import { DataFreshnessIndicator, DataModeBadge, WarningList } from '../../shared/ui/badges'
import { EventCard } from '../../shared/ui/cards'
import { NewsSourceLink } from '../../shared/ui/NewsSourceLink'
import { EmptyState, LoadingSkeleton, RefreshButton, SurfaceCard } from '../../shared/ui/primitives'
import { formatDateTime } from '../../shared/lib/format'
import type { EventViewModel } from '../../shared/types/view-models'

const instrumentOptions = [
  { value: 'all', label: 'Todos' },
  { value: 'equity', label: 'Equities' },
  { value: 'etf', label: 'ETF' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'commodity', label: 'Commodities' },
  { value: 'credit', label: 'Crédito' },
]

const topicOptions = [
  { value: 'all', label: 'Todos los temas' },
  { value: 'direct', label: 'Impacto directo' },
  { value: 'sector', label: 'Sector / benchmark' },
  { value: 'macro', label: 'Macro / commodities' },
]

function independentSourceNames(event: EventViewModel): string {
  return event.sources
    .filter(source => !source.isAggregator)
    .map(source => source.name)
    .join(', ')
}

function matchesTopicScope(event: EventViewModel, topicScope: string): boolean {
  if (topicScope === 'all') return true
  if (topicScope === 'direct') {
    return event.relatedAssets.some(relation => relation.relationship === 'direct')
  }
  if (topicScope === 'sector') {
    return event.relatedAssets.some(relation => relation.relationship === 'sector')
  }
  if (topicScope === 'macro') {
    return event.relatedAssets.some(relation =>
      ['macro', 'commodity', 'credit'].includes(relation.relationship),
    )
  }
  return true
}

export function RadarPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards')
  const filters = useMemo(
    () => ({
      instrumentType: searchParams.get('instrumentType') ?? 'all',
      asset: searchParams.get('asset') ?? '',
      publishedAfter: searchParams.get('publishedAfter') ?? '',
      topicScope: searchParams.get('topicScope') ?? 'all',
    }),
    [searchParams],
  )
  const highlightEventId = searchParams.get('event') ?? ''
  const eventsQuery = useEventsQuery({
    instrumentType: filters.instrumentType,
    asset: filters.asset,
    publishedAfter: filters.publishedAfter,
  })
  const highlightedEventQuery = useEventQuery(highlightEventId)
  const events = useMemo(
    () => (eventsQuery.data?.items ?? []).filter(event => matchesTopicScope(event, filters.topicScope)),
    [eventsQuery.data?.items, filters.topicScope],
  )
  const meta = eventsQuery.data?.meta
  const analysis = useStartAnalysis(events)
  const highlightedEvent =
    highlightedEventQuery.data ??
    events.find(event => event.id === highlightEventId) ??
    null

  useEffect(() => {
    if (!highlightEventId) return
    document
      .querySelector(`[data-event-id="${highlightEventId}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [highlightEventId, events, viewMode])

  if (eventsQuery.isLoading) return <LoadingSkeleton rows={10} />

  return (
    <div className="page-stack">
      <SurfaceCard
        eyebrow="02 · Radar"
        title="Eventos, fuentes y contexto verificable"
        className="page-intro-panel"
        tourTarget="radar-overview"
        action={
          <div className="surface-card__actions">
            <RefreshButton onClick={() => eventsQuery.refetch()} busy={eventsQuery.isFetching} />
            <button
              className="primary-button"
              type="button"
              onClick={() => {
                void analysis.startAnalysis()
              }}
              disabled={analysis.isStarting || !analysis.canStart}
            >
              <Sparkles size={16} />
              {analysis.isStarting ? 'Lanzando análisis' : 'Nuevo análisis'}
            </button>
          </div>
        }
      >
        <div className="toolbar-grid">
          <label className="field">
            <span>Instrumento</span>
            <select
              value={filters.instrumentType}
              onChange={event =>
                setSearchParams(previous => {
                  const next = new URLSearchParams(previous)
                  next.set('instrumentType', event.target.value)
                  return next
                })
              }
            >
              {instrumentOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Tema</span>
            <select
              value={filters.topicScope}
              onChange={event =>
                setSearchParams(previous => {
                  const next = new URLSearchParams(previous)
                  next.set('topicScope', event.target.value)
                  return next
                })
              }
            >
              {topicOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Activo</span>
            <input
              value={filters.asset}
              placeholder="AAPL, BTC, SPY"
              onChange={event =>
                setSearchParams(previous => {
                  const next = new URLSearchParams(previous)
                  if (event.target.value) next.set('asset', event.target.value)
                  else next.delete('asset')
                  return next
                })
              }
            />
          </label>

          <label className="field">
            <span>Publicado despues de</span>
            <input
              type="date"
              value={filters.publishedAfter}
              onChange={event =>
                setSearchParams(previous => {
                  const next = new URLSearchParams(previous)
                  if (event.target.value) next.set('publishedAfter', event.target.value)
                  else next.delete('publishedAfter')
                  return next
                })
              }
            />
          </label>

          <div className="segmented-control">
            <button className={viewMode === 'cards' ? 'active' : ''} onClick={() => setViewMode('cards')} type="button">
              Tarjetas
            </button>
            <button className={viewMode === 'table' ? 'active' : ''} onClick={() => setViewMode('table')} type="button">
              Tabla
            </button>
          </div>
        </div>

        {meta ? (
          <div className="data-status-row">
            <DataModeBadge mode={meta.dataMode} />
            <DataFreshnessIndicator asOf={meta.dataAsOf} retrievedAt={meta.retrievedAt} />
          </div>
        ) : null}
        {meta ? <WarningList warnings={meta.warnings} /> : null}
      </SurfaceCard>

      {highlightedEvent ? (
        <SurfaceCard eyebrow="Evento seleccionado" title={highlightedEvent.title} className="radar-event-focus">
          <p>{highlightedEvent.summary}</p>
          <div className="data-points">
            <span>{formatDateTime(highlightedEvent.eventAt)}</span>
            <span>{highlightedEvent.independentSourceCount} fuentes independientes</span>
            <span>{highlightedEvent.relatedAssets.map(asset => asset.symbol).join(', ')}</span>
          </div>
          <div className="stack-list">
            {highlightedEvent.articles.map(article => {
              const source = highlightedEvent.sources.find(item => item.id === article.sourceId)
              return (
                <article key={article.id} className="timeline-item">
                  <div>
                    <strong>{source?.name ?? 'Fuente'}</strong>
                    <span>{formatDateTime(article.publishedAt)}</span>
                  </div>
                  <p>{article.headline}</p>
                  <NewsSourceLink url={article.url} linkable={article.linkable ?? false} label="Abrir artículo" />
                </article>
              )
            })}
          </div>
        </SurfaceCard>
      ) : null}

      {!events.length ? (
        <EmptyState title="Sin eventos para esos filtros" description="Ajusta instrumento, tema, activo o fecha para recuperar el radar." />
      ) : viewMode === 'cards' ? (
        <div className="stack-list" data-tour-target="radar-events">
          {events.map(event => (
            <div
              className={event.id === highlightEventId ? 'list-card-wrap list-card-wrap--highlighted' : 'list-card-wrap'}
              data-event-id={event.id}
              key={event.id}
            >
              <EventCard event={event} />
            </div>
          ))}
        </div>
      ) : (
        <SurfaceCard title="Vista tabular" tourTarget="radar-events">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Evento</th>
                  <th>Fecha</th>
                  <th>Activos</th>
                  <th>Fuentes</th>
                </tr>
              </thead>
              <tbody>
                {events.map(event => (
                  <tr
                    className={event.id === highlightEventId ? 'data-table__row--highlighted' : undefined}
                    data-event-id={event.id}
                    key={event.id}
                  >
                    <td>{event.title}</td>
                    <td>{formatDateTime(event.eventAt)}</td>
                    <td>{event.relatedAssets.map(asset => asset.symbol).join(', ')}</td>
                    <td>{independentSourceNames(event) || event.independentSourceCount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SurfaceCard>
      )}
    </div>
  )
}
