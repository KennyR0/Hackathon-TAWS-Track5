import { useParams } from 'react-router-dom'
import { useBriefingQuery, useSignalsQuery } from '../../shared/api/queries'
import { ReviewStatusBadge, WarningList } from '../../shared/ui/badges'
import { BackToHomeButton, EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { formatDateTime } from '../../shared/lib/format'

export function BriefingDetailPage() {
  const { briefingId = '' } = useParams()
  const briefingQuery = useBriefingQuery(briefingId)
  const signalsQuery = useSignalsQuery()

  if (briefingQuery.isLoading) return <LoadingSkeleton rows={8} />
  if (!briefingQuery.data) return <EmptyState title="Briefing no encontrado" description="Ese briefing no esta disponible en este navegador o no pudo hidratarse." />

  const briefing = briefingQuery.data
  const signals = signalsQuery.data?.items ?? []

  return (
    <div className="page-stack">
      <BackToHomeButton />
      <SurfaceCard eyebrow={briefing.watchlist.name} title={`Briefing ${briefing.status}`}>
        <p className="hero-copy">{briefing.executiveSummary}</p>
        <div className="data-points">
          <span>{formatDateTime(briefing.createdAt)}</span>
          <span>{briefing.prioritizedSignals.length} señales priorizadas</span>
          <span>{briefing.reviewTasks.filter(task => task.status === 'open').length} tareas abiertas</span>
        </div>
        <WarningList warnings={briefing.meta.warnings} />
      </SurfaceCard>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Señales" title="Prioridades del briefing">
          <div className="stack-list">
            {briefing.prioritizedSignals.map(item => {
              const signal = signals.find(signalCandidate => signalCandidate.id === item.signalId)
              return (
                <article className="list-card" key={item.signalId}>
                  <div className="list-card__header">
                    <div>
                      <p className="section-eyebrow">{signal?.asset.symbol ?? item.signalId}</p>
                      <h3>{signal?.thesis ?? item.reason}</h3>
                    </div>
                    <ReviewStatusBadge status={item.review.status} />
                  </div>
                  <p>{item.reason}</p>
                  <ul className="text-list">
                    {item.suggestedResearchActions.map(action => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                </article>
              )
            })}
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Review tasks" title="Pendientes embebidos">
          {briefing.reviewTasks.length ? (
            <div className="stack-list">
              {briefing.reviewTasks.map(task => (
                <article className="timeline-item" key={task.id}>
                  <div>
                    <strong>{task.title}</strong>
                    <span>{task.kind}</span>
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
