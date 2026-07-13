import { useParams } from 'react-router-dom'
import { useEventQuery, useMarketSnapshotsQuery, useSignalDetailQuery, useSimilarEventsQuery } from '../../shared/api/queries'
import { ConfidenceBreakdown } from '../../shared/ui/charts/ConfidenceBreakdown'
import { ReactionChart } from '../../shared/ui/charts/ReactionChart'
import { AnalysisStatusBadge, ImpactBadge, ReviewStatusBadge, WarningList } from '../../shared/ui/badges'
import { BackToHomeButton, EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { NewsSourceLink } from '../../shared/ui/NewsSourceLink'
import { PriceReactionMetrics, SignalDisclaimer } from '../../shared/ui/compliance'
import { formatDateTime } from '../../shared/lib/format'
import { ReviewComposer } from '../reviews/ReviewComposer'

export function SignalDetailPage() {
  const { signalId = '' } = useParams()
  const signalQuery = useSignalDetailQuery(signalId)
  const eventQuery = useEventQuery(signalQuery.data?.signal.eventId ?? '')
  const similarEventsQuery = useSimilarEventsQuery(signalQuery.data?.signal.eventId ?? '', {
    enabled: Boolean(signalQuery.data?.signal.eventId),
  })
  const snapshotsQuery = useMarketSnapshotsQuery(
    { asset: signalQuery.data?.signal.asset.symbol, interval: '1d' },
    { enabled: Boolean(signalQuery.data?.signal.asset.symbol) },
  )

  if (signalQuery.isLoading) return <LoadingSkeleton rows={12} />
  if (!signalQuery.data) return <EmptyState title="Señal no encontrada" description="No logramos cargar la señal solicitada." />

  const { signal, evidence, reviews } = signalQuery.data
  const snapshot = snapshotsQuery.data?.items[0] ?? null
  const supportiveEvidence = evidence.filter(item => item.supportsSignal)
  const contradictoryEvidence = evidence.filter(item => !item.supportsSignal)

  return (
    <div className="page-stack">
      <BackToHomeButton />
      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow={`${signal.asset.symbol} · Tesis`} title={signal.asset.name} className="signal-hero" tourTarget="signal-thesis">
          <div className="badge-row">
            <ImpactBadge impact={signal.impact} />
            <ReviewStatusBadge status={signal.reviewStatus} />
            <AnalysisStatusBadge status={signal.analysisStatus} />
          </div>
          <p className="hero-copy">{signal.thesis ?? 'La API todavía no devolvió una tesis sintetizada para esta señal.'}</p>
          <div className="data-points">
            <span>{formatDateTime(signal.updatedAt)}</span>
            <span>{signal.evidenceIds.length} evidencias</span>
            <span>{signal.counterEvidenceIds.length} contraevidencias</span>
          </div>
          <WarningList warnings={signal.meta.warnings} />
          <SignalDisclaimer text={signal.disclaimer} />
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
        <ReactionChart signal={signal} snapshot={snapshot} />
        <ConfidenceBreakdown signal={signal} />
      </section>

      <SurfaceCard eyebrow="Reacción verificable" title="Comparación con benchmark y volumen">
        <PriceReactionMetrics signal={signal} />
      </SurfaceCard>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Ledger · Evidencia favorable" title="Soportes trazables" className="evidence-ledger" tourTarget="signal-evidence">
          <div className="stack-list">
            {supportiveEvidence.map(item => (
              <article key={item.id} className="evidence-card">
                <strong>{item.claim}</strong>
                <p>{item.excerpt ?? 'Sin excerpt. El backend solo entrego el claim y la fuente.'}</p>
                <div className="data-points">
                  <span>{item.evidenceType}</span>
                  <NewsSourceLink url={item.sourceUrl} linkable={item.linkable} label="Fuente original" />
                </div>
              </article>
            ))}
          </div>
        </SurfaceCard>

        <SurfaceCard eyebrow="Ledger · Contraevidencia" title="Abstención y contradicción" className="evidence-ledger evidence-ledger--counter">
          {contradictoryEvidence.length ? (
            <div className="stack-list">
              {contradictoryEvidence.map(item => (
                <article key={item.id} className="evidence-card evidence-card--negative">
                  <strong>{item.claim}</strong>
                  <p>{item.excerpt ?? 'Sin excerpt.'}</p>
                  <div className="data-points">
                    <span>{item.evidenceType}</span>
                    <NewsSourceLink url={item.sourceUrl} linkable={item.linkable} label="Fuente original" />
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="Sin contraevidencia explícita" description="El backend no devolvió evidencia que contradiga la hipótesis para esta señal." />
          )}
        </SurfaceCard>
      </section>

      <SurfaceCard eyebrow="Historicos similares" title="Comparacion semantica deterministica">
        {similarEventsQuery.data?.items.length ? (
          <div className="stack-list">
            {similarEventsQuery.data.items.slice(0, 3).map(item => (
              <article key={item.eventId} className="timeline-item">
                <div>
                  <strong>{item.title}</strong>
                  <span>{Math.round(item.similarityScore * 100)}%</span>
                </div>
                <p>{item.rationale}</p>
                <small>{formatDateTime(item.eventAt)}</small>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="Sin comparables" description="No hay eventos historicos suficientes para esta senal." />
        )}
      </SurfaceCard>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Control humano" title="Decisión y justificación" className="review-console" tourTarget="review-console">
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
