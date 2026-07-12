import { useRecentRunsQuery } from '../../shared/api/queries'
import { RunCard } from '../../shared/ui/cards'
import { EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'

export function AuditPage() {
  const runs = useRecentRunsQuery()
  const hydratedRuns = runs.map(item => item.data).filter((run): run is NonNullable<typeof run> => Boolean(run))

  if (runs.some(item => item.isLoading)) return <LoadingSkeleton rows={8} />

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="06 · Control" title="Auditoría reproducible" className="page-intro-panel">
        <p className="inline-hint">La lista se alimenta de runs disparados desde este navegador y se rehidrata desde el backend en cada visita.</p>
      </SurfaceCard>
      {hydratedRuns.length ? (
        <div className="stack-list">
          {hydratedRuns.map(run => (
            <RunCard key={run.id} run={run} />
          ))}
        </div>
      ) : (
        <EmptyState title="Sin runs almacenados" description="Todavia no hay ejecuciones locales recientes para auditar." />
      )}
    </div>
  )
}
