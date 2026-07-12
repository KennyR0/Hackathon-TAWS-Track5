import { useParams } from 'react-router-dom'
import { useEventQuery, useSignalDetailQuery } from '../../shared/api/queries'
import { ConfidenceBreakdown } from '../../shared/ui/charts/ConfidenceBreakdown'
import { ReactionChart } from '../../shared/ui/charts/ReactionChart'
import { AnalysisStatusBadge, ImpactBadge, ReviewStatusBadge, WarningList } from '../../shared/ui/badges'
import { EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { formatDateTime } from '../../shared/lib/format'
import { ReviewComposer } from '../reviews/ReviewComposer'

export function SignalDetailPage() {
  const { signalId = '' } = useParams()
  const signalQuery = useSignalDetailQuery(signalId)
  const eventQuery = useEventQuery(signalQuery.data?.signal.eventId ?? '')

  if (signalQuery.isLoading) return <LoadingSkeleton rows={12} />
  if (!signalQuery.data) return <EmptyState title="Senal no encontrada" description="No logramos cargar la senal solicitada." />

  const { signal, evidence, reviews } = signalQuery.data
  const supportiveEvidence = evidence.filter(item => item.supportsSignal)
  const contradictoryEvidence = evidence.filter(item => !item.supportsSignal)

  return (
    <div className="page-stack">
      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow={signal.asset.symbol} title={signal.asset.name}>
          <div className="badge-row">
            <ImpactBadge impact={signal.impact} />
            <ReviewStatusBadge status={signal.reviewStatus} />
            <AnalysisStatusBadge status={signal.analysisStatus} />
          </div>
          <p className="hero-copy">{signal.thesis ?? 'La API todavia no devolvio una tesis sintetizada para esta senal.'}</p>
          <div className="data-points">
            <span>{formatDateTime(signal.updatedAt)}</span>
            <span>{signal.evidenceIds.length} evidencias</span>
            <span>{signal.counterEvidenceIds.length} contraevidencias</span>
          </div>
          <WarningList warnings={signal.meta.warnings} />
        </SurfaceCard>

        <SurfaceCard eyebrow="Evento vinculado" title={eventQuery.data?.title ?? 'Cargando evento'}>
          <p>{eventQuery.data?.summary ?? 'Estamos resolviendo el evento asociado desde el backend.'}</p>
          <div className="data-points">
            <span>{eventQuery.data ? formatDateTime(eventQuery.data.eventAt) : 'Sin fecha'}</span>
            <span>{eventQuery.data?.independentSourceCount ?? 0} fuentes independientes</span>
          </div>
        </SurfaceCard>
      </section>

      <section className="content-grid content-grid--wide">
        <ReactionChart signal={signal} />
        <ConfidenceBreakdown signal={signal} />
      </section>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Evidencia favorable" title="Soportes trazables">
          <div className="stack-list">
            {supportiveEvidence.map(item => (
              <article key={item.id} className="evidence-card">
                <strong>{item.claim}</strong>
                <p>{item.excerpt ?? 'Sin excerpt. El backend solo entrego el claim y la fuente.'}</p>
                <div className="data-points">
                  <span>{item.evidenceType}</span>
                  <a href={item.sourceUrl} rel="noreferrer" target="_blank">
                    Fuente original
                  </a>
                </div>
              </article>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Contraevidencia" title="Senales de abstencion y contradiccion">
          {contradictoryEvidence.length ? (
            <div className="stack-list">
              {contradictoryEvidence.map(item => (
                <article key={item.id} className="evidence-card evidence-card--negative">
                  <strong>{item.claim}</strong>
                  <p>{item.excerpt ?? 'Sin excerpt.'}</p>
                  <div className="data-points">
                    <span>{item.evidenceType}</span>
                    <a href={item.sourceUrl} rel="noreferrer" target="_blank">
                      Fuente original
                    </a>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="Sin contraevidencia explicita" description="El backend no devolvio evidencia que contradiga la hipotesis para esta senal." />
          )}
        </SurfaceCard>
      </section>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Revision humana" title="Decision y justificacion">
          <ReviewComposer signalId={signal.id} currentStatus={signal.reviewStatus} />
          <div className="stack-list">
            {reviews.map(review => (
              <article key={review.id} className="timeline-item">
                <div>
                  <strong>{review.reviewedBy.name}</strong>
                  <span>{review.status}</span>
                </div>
                <p>{review.justification}</p>
                <small>{formatDateTime(review.reviewedAt)}</small>
              </article>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Supuestos" title="Condiciones de invalidez y tareas de investigacion">
          <div className="split-list">
            <div>
              <h3>Supuestos</h3>
              <ul className="text-list">
                {signal.assumptions.map(item => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Invalidaciones</h3>
              <ul className="text-list">
                {signal.invalidationConditions.map(item => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </SurfaceCard>
      </section>
    </div>
  )
}
