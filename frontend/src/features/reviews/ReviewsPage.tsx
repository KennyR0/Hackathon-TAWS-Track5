import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useEventsQuery, useSignalsQuery } from '../../shared/api/queries'
import { deriveAssetSummaries } from '../../shared/api/mappers'
import { ReviewStatusBadge } from '../../shared/ui/badges'
import { EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { formatConfidence } from '../../shared/lib/format'

export function ReviewsPage() {
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const [selectedStatus, setSelectedStatus] = useState('all')

  const queue = useMemo(() => {
    const signals = signalsQuery.data?.items ?? []
    const events = eventsQuery.data?.items ?? []
    const assets = deriveAssetSummaries(signals, events)
    return signals
      .filter(signal => selectedStatus === 'all' || signal.reviewStatus === selectedStatus)
      .map(signal => ({
        signal,
        asset: assets.find(item => item.symbol === signal.asset.symbol) ?? null,
        event: events.find(item => item.id === signal.eventId) ?? null,
      }))
  }, [eventsQuery.data?.items, selectedStatus, signalsQuery.data?.items])

  if (signalsQuery.isLoading || eventsQuery.isLoading) return <LoadingSkeleton rows={10} />

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="04 · Revisión" title="Cola de decisiones humanas" className="page-intro-panel">
        <div className="toolbar-grid">
          <label className="field">
            <span>Estado</span>
            <select value={selectedStatus} onChange={event => setSelectedStatus(event.target.value)}>
              <option value="all">Todos</option>
              <option value="pending_review">Pending review</option>
              <option value="reviewed">Reviewed</option>
              <option value="escalated">Escalated</option>
              <option value="discarded">Discarded</option>
            </select>
          </label>
        </div>
      </SurfaceCard>

      {!queue.length ? (
        <EmptyState title="Sin trabajo en cola" description="No hay señales que coincidan con ese estado de revisión." />
      ) : (
        <div className="stack-list">
          {queue.map(({ signal, asset, event }) => (
            <article key={signal.id} className="list-card">
              <div className="list-card__header">
                <div>
                  <p className="section-eyebrow">{signal.asset.symbol}</p>
                  <h3>{signal.thesis ?? signal.asset.name}</h3>
                </div>
                <ReviewStatusBadge status={signal.reviewStatus} />
              </div>
              <div className="data-points">
                <span>{event?.title ?? 'Sin evento resuelto'}</span>
                <span>Confianza {formatConfidence(signal.confidence)}</span>
                <span>{asset ? `${asset.signalCount} señales del activo` : 'Cobertura puntual'}</span>
              </div>
              <div className="card-actions">
                <Link className="text-link" to={`/signals/${signal.id}`}>
                  Revisar señal
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
