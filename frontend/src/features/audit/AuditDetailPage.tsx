import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { queryKeys, useRunQuery } from '../../shared/api/queries'
import { subscribeToAnalysisStream } from '../../shared/api/sse'
import { AnalysisStatusBadge, WarningList } from '../../shared/ui/badges'
import { BackToHomeButton, EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { compactId, formatDateTime } from '../../shared/lib/format'
import type { ApiSseEvent } from '../../shared/api/contracts'

export function AuditDetailPage() {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const runQuery = useRunQuery(runId)
  const [streamEvents, setStreamEvents] = useState<ApiSseEvent[]>([])
  const [lastEventId, setLastEventId] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return

    return subscribeToAnalysisStream({
      runId,
      lastEventId,
      onStep: (event, currentLastEventId) => {
        setStreamEvents(previous => (previous.some(item => item.id === event.id) ? previous : [...previous, event]))
        setLastEventId(currentLastEventId)
        void queryClient.invalidateQueries({ queryKey: queryKeys.run(runId) })
      },
    })
  }, [lastEventId, queryClient, runId])

  const mergedSteps = useMemo(() => {
    const persisted = runQuery.data?.steps ?? []
    return [...persisted, ...streamEvents.filter(event => !persisted.some(step => step.id === event.id))]
      .toSorted((left, right) => left.timestamp.localeCompare(right.timestamp))
  }, [runQuery.data?.steps, streamEvents])

  if (runQuery.isLoading) return <LoadingSkeleton rows={12} />
  if (!runQuery.data) return <EmptyState title="Run no encontrado" description="No logramos recuperar la ejecucion solicitada." />

  const run = runQuery.data

  return (
    <div className="page-stack">
      <BackToHomeButton />
      <SurfaceCard eyebrow="Ejecución reproducible" title={`Run ${compactId(run.id)}`} className="audit-hero">
        <div className="badge-row">
          <AnalysisStatusBadge status={run.status} />
        </div>
        <div className="data-points">
          <span>Inicio {formatDateTime(run.startedAt)}</span>
          <span>Fin {formatDateTime(run.finishedAt)}</span>
          <span>{run.steps.length} pasos persistidos</span>
        </div>
        <WarningList warnings={run.warnings} />
      </SurfaceCard>

      <SurfaceCard eyebrow="Timeline" title="Pasos del workflow" className="audit-timeline">
        <div className="stack-list">
          {mergedSteps.map(step => (
            <article className="timeline-item" key={step.id}>
              <div>
                <strong>{step.node}</strong>
                <span>{step.status}</span>
              </div>
              <small>{formatDateTime(step.timestamp)}</small>
              <pre className="payload-block">{JSON.stringify(step.payload, null, 2)}</pre>
            </article>
          ))}
        </div>
      </SurfaceCard>
    </div>
  )
}
