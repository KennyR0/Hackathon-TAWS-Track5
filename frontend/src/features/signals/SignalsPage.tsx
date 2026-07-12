import { useMemo, useState } from 'react'
import { useSignalsQuery } from '../../shared/api/queries'
import { SignalCard } from '../../shared/ui/cards'
import { EmptyState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'

export function SignalsPage() {
  const signalsQuery = useSignalsQuery()
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')

  const filteredSignals = useMemo(() => {
    const items = signalsQuery.data?.items ?? []
    return items.filter(signal => {
      const matchesStatus = statusFilter === 'all' || signal.reviewStatus === statusFilter || signal.analysisStatus === statusFilter
      const matchesSearch =
        !search ||
        signal.asset.symbol.toLowerCase().includes(search.toLowerCase()) ||
        signal.asset.name.toLowerCase().includes(search.toLowerCase()) ||
        signal.id.toLowerCase().includes(search.toLowerCase())
      return matchesStatus && matchesSearch
    })
  }, [search, signalsQuery.data?.items, statusFilter])

  if (signalsQuery.isLoading) return <LoadingSkeleton rows={10} />

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="Señales" title="Cola explicable y accionable">
        <div className="toolbar-grid">
          <label className="field">
            <span>Buscar</span>
            <input value={search} onChange={event => setSearch(event.target.value)} placeholder="AAPL, signalId, activo" />
          </label>
          <label className="field">
            <span>Estado</span>
            <select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>
              <option value="all">Todos</option>
              <option value="pending_review">Pending review</option>
              <option value="reviewed">Reviewed</option>
              <option value="escalated">Escalated</option>
              <option value="discarded">Discarded</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
            </select>
          </label>
        </div>
      </SurfaceCard>

      {!filteredSignals.length ? (
        <EmptyState title="Sin resultados" description="No encontramos señales con ese filtro." />
      ) : (
        <div className="stack-list">
          {filteredSignals.map(signal => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      )}
    </div>
  )
}
