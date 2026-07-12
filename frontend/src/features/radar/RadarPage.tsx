import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useEventsQuery } from '../../shared/api/queries'
import { DataFreshnessIndicator, WarningList } from '../../shared/ui/badges'
import { EventCard } from '../../shared/ui/cards'
import { EmptyState, LoadingSkeleton, RefreshButton, SurfaceCard } from '../../shared/ui/primitives'

const instrumentOptions = [
  { value: 'all', label: 'Todos' },
  { value: 'equity', label: 'Equities' },
  { value: 'etf', label: 'ETF' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'commodity', label: 'Commodities' },
]

export function RadarPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards')
  const filters = useMemo(
    () => ({
      instrumentType: searchParams.get('instrumentType') ?? 'all',
      asset: searchParams.get('asset') ?? '',
      publishedAfter: searchParams.get('publishedAfter') ?? '',
    }),
    [searchParams],
  )
  const eventsQuery = useEventsQuery(filters)

  if (eventsQuery.isLoading) return <LoadingSkeleton rows={10} />

  const events = eventsQuery.data?.items ?? []
  const meta = eventsQuery.data?.meta

  return (
    <div className="page-stack">
      <SurfaceCard
        eyebrow="Radar de mercado"
        title="Eventos verificados y filtros operativos"
        action={<RefreshButton onClick={() => eventsQuery.refetch()} busy={eventsQuery.isFetching} />}
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

        {meta ? <DataFreshnessIndicator asOf={meta.dataAsOf} retrievedAt={meta.retrievedAt} /> : null}
        {meta ? <WarningList warnings={meta.warnings} /> : null}
      </SurfaceCard>

      {!events.length ? (
        <EmptyState title="Sin eventos para esos filtros" description="Ajusta instrumento, activo o fecha para recuperar el radar." />
      ) : viewMode === 'cards' ? (
        <div className="stack-list">
          {events.map(event => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      ) : (
        <SurfaceCard title="Vista tabular">
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
                  <tr key={event.id}>
                    <td>{event.title}</td>
                    <td>{new Date(event.eventAt).toLocaleDateString('es-EC')}</td>
                    <td>{event.relatedAssets.map(asset => asset.symbol).join(', ')}</td>
                    <td>{event.independentSourceCount}</td>
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
