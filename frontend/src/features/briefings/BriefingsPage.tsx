import { useNavigate } from 'react-router-dom'
import { useCreateBriefingMutation, useRecentBriefingsQuery, useSignalsQuery, useWatchlistQuery } from '../../shared/api/queries'
import { BriefingCard } from '../../shared/ui/cards'
import { EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'

export function BriefingsPage() {
  const navigate = useNavigate()
  const signalsQuery = useSignalsQuery()
  const watchlistQuery = useWatchlistQuery()
  const createBriefing = useCreateBriefingMutation()
  const recentBriefings = useRecentBriefingsQuery()
  const briefings = recentBriefings
    .map(item => item.data)
    .filter((briefing): briefing is NonNullable<typeof briefing> => Boolean(briefing))

  if (signalsQuery.isLoading) return <LoadingSkeleton rows={10} />

  const signals = signalsQuery.data?.items ?? []
  const canCreateShareable = signals.every(signal => signal.analysisStatus === 'completed' && signal.reviewStatus === 'reviewed')

  const handleCreate = async (status: 'draft' | 'shareable') => {
    const response = await createBriefing.mutateAsync({
      signalIds: signals.map(signal => signal.id),
      status,
      watchlistId: watchlistQuery.data?.id ?? 'watchlist_demo_global',
    })
    navigate(`/briefings/${response.data.briefingId}`)
  }

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="05 · Operaciones" title="Briefings" className="page-intro-panel">
        <div className="card-actions">
          <button
            className="primary-button"
            type="button"
            onClick={() => handleCreate('draft')}
            disabled={createBriefing.isPending || !signals.length || !watchlistQuery.data}
          >
            Crear draft
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => handleCreate('shareable')}
            disabled={createBriefing.isPending || !canCreateShareable || !watchlistQuery.data}
          >
            Crear shareable
          </button>
        </div>
        <p className="inline-hint">Shareable solo se habilita cuando todas las señales incluidas están completadas y revisadas.</p>
      </SurfaceCard>

      {recentBriefings.some(item => item.isLoading) ? (
        <LoadingSkeleton rows={6} />
      ) : briefings.length ? (
        <div className="stack-list">
          {briefings.map(briefing => (
            <BriefingCard key={briefing.id} briefing={briefing} />
          ))}
        </div>
      ) : (
        <EmptyState title="Sin briefings recientes" description="Aun no se ha creado un briefing desde este navegador." />
      )}
    </div>
  )
}
