import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import { mapEventView } from '../../shared/api/mappers'
import { queryKeys, useBriefingQuery, useSignalsQuery } from '../../shared/api/queries'
import { formatDateTime, toSentenceCase } from '../../shared/lib/format'
import { ReviewStatusBadge, WarningList } from '../../shared/ui/badges'
import { MetricCard } from '../../shared/ui/cards'
import { PriceReactionMetrics, SignalDisclaimer } from '../../shared/ui/compliance'
import { BackToHomeButton, EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { NewsSourceLink } from '../../shared/ui/NewsSourceLink'
import type { EventViewModel } from '../../shared/types/view-models'

export function BriefingDetailPage() {
  const { briefingId = '' } = useParams()
  const briefingQuery = useBriefingQuery(briefingId)
  const signalsQuery = useSignalsQuery()

  const briefing = briefingQuery.data
  const signalItems = signalsQuery.data?.items

  const eventIds = useMemo(() => {
    if (!briefing || !signalItems) return []
    return [
      ...new Set(
        briefing.prioritizedSignals
          .map(item => signalItems.find(signalCandidate => signalCandidate.id === item.signalId)?.eventId)
          .filter((eventId): eventId is string => Boolean(eventId)),
      ),
    ]
  }, [briefing, signalItems])

  const eventQueries = useQueries({
    queries: eventIds.map(eventId => ({
      queryKey: queryKeys.event(eventId),
      queryFn: async () => {
        const payload = await apiClient.getEvent(eventId)
        return mapEventView(payload.data, payload.meta)
      },
      enabled: Boolean(briefing),
    })),
  })

  const eventsById = useMemo(() => {
    const map = new Map<string, EventViewModel>()
    eventQueries.forEach((query, index) => {
      if (query.data) map.set(eventIds[index], query.data)
    })
    return map
  }, [eventIds, eventQueries])

  if (briefingQuery.isLoading) return <LoadingSkeleton rows={8} />
  if (!briefing) return <EmptyState title="Briefing no encontrado" description="Ese briefing no esta disponible en este navegador o no pudo hidratarse." />

  const signals = signalItems ?? []

  const reviewSummary = briefing.humanReviewSummary

  return (
    <div className="page-stack">
      <BackToHomeButton />
      <SurfaceCard eyebrow={`${briefing.watchlist.name} · ${briefing.status}`} title="Lectura ejecutiva" className="briefing-paper" tourTarget="briefing-report">
        <p className="hero-copy">{briefing.executiveSummary}</p>
        <div className="data-points">
          <span>{formatDateTime(briefing.createdAt)}</span>
          <span>{briefing.prioritizedSignals.length} señales priorizadas</span>
          <span>{briefing.reviewTasks.filter(task => task.status === 'open').length} tareas abiertas</span>
        </div>
        <WarningList warnings={briefing.meta.warnings} />
        <SignalDisclaimer />
      </SurfaceCard>

      <SurfaceCard eyebrow="Resumen de revisión" title="Estado humano antes de compartir">
        <div className="price-reaction-grid">
          <MetricCard label="Revisadas" value={String(reviewSummary.reviewed)} />
          <MetricCard label="Escaladas" value={String(reviewSummary.escalated)} />
          <MetricCard label="Descartadas" value={String(reviewSummary.discarded)} />
          <MetricCard label="Pendientes" value={String(reviewSummary.pendingReview)} hint={`${reviewSummary.totalSignals} señales en total`} />
        </div>
      </SurfaceCard>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Señales" title="Prioridades del briefing">
          <div className="stack-list">
            {briefing.prioritizedSignals.map(item => {
              const signal = signals.find(signalCandidate => signalCandidate.id === item.signalId)
              const event = signal ? eventsById.get(signal.eventId) ?? null : null
              const sourceNames = event?.sources.filter(source => !source.isAggregator).map(source => source.name).join(', ')

              return (
                <article className="list-card" key={item.signalId}>
                  <div className="list-card__header">
                    <div>
                      <p className="section-eyebrow">{signal?.asset.symbol ?? item.signalId}</p>
                      <h3>{signal?.thesis ?? item.reason}</h3>
                    </div>
                    <ReviewStatusBadge status={item.review.status} />
                  </div>

                  {event ? (
                    <div className="briefing-linked-event">
                      <p className="section-eyebrow">Noticia vinculada</p>
                      <strong>{event.title}</strong>
                      <p>{event.summary}</p>
                      <div className="data-points">
                        <span>{formatDateTime(event.eventAt)}</span>
                        <span>{event.independentSourceCount} fuentes</span>
                        {sourceNames ? <span>{sourceNames}</span> : null}
                        {event.mainArticle ? (
                          <NewsSourceLink
                            url={event.mainArticle.url}
                            linkable={event.mainArticleLinkable}
                            label="Fuente principal"
                          />
                        ) : null}
                      </div>
                    </div>
                  ) : (
                    <p>Resolviendo la noticia asociada desde el backend.</p>
                  )}

                  {signal ? (
                    <div className="briefing-linked-movement">
                      <p className="section-eyebrow">Movimiento asociado</p>
                      <PriceReactionMetrics signal={signal} />
                    </div>
                  ) : null}

                  <p>{item.reason}</p>
                  <ul className="text-list">
                    {item.suggestedResearchActions.map(action => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>

                  {signal ? (
                    <div className="card-actions">
                      <Link className="text-link" to={`/signals/${signal.id}`}>
                        Abrir señal
                      </Link>
                      {event ? (
                        <Link className="text-link" to={`/radar?event=${event.id}`}>
                          Ver evento en radar
                        </Link>
                      ) : null}
                    </div>
                  ) : null}
                </article>
              )
            })}
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Control editorial" title="Antes de compartir" className="editorial-control">
          {briefing.reviewTasks.length ? (
            <div className="stack-list">
              {briefing.reviewTasks.map(task => (
                <article className="timeline-item" key={task.id}>
                  <div>
                    <strong>{task.title}</strong>
                    <span>{toSentenceCase(task.kind)}</span>
                  </div>
                  <p>{task.description}</p>
                  <small>{task.status === 'resolved' ? `Resuelta ${formatDateTime(task.resolvedAt)}` : 'Pendiente'}</small>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="Sin tareas abiertas" description="Este briefing no arrastra revisiones ni escalaciones pendientes." />
          )}
        </SurfaceCard>
      </section>
    </div>
  )
}
