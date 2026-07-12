import { Menu, Search, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { navigationItems } from './navigation'
import { AgentStatus, DataFreshnessIndicator, DataModeBadge } from '../../shared/ui/badges'
import { useCreateAnalysisMutation, useEventsQuery, useRecentRunsQuery, useSignalsQuery } from '../../shared/api/queries'
import { compactId } from '../../shared/lib/format'

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const recentRuns = useRecentRunsQuery()
  const latestRun = useMemo(() => recentRuns.map(item => item.data).find(Boolean), [recentRuns])
  const createAnalysis = useCreateAnalysisMutation()

  const handleSearch = () => {
    const trimmed = query.trim()
    if (!trimmed) return
    const signal = signalsQuery.data?.items.find(item => item.asset.symbol.toLowerCase() === trimmed.toLowerCase() || item.id === trimmed)
    if (signal) {
      navigate(`/signals/${signal.id}`)
      return
    }
    navigate(`/radar?asset=${encodeURIComponent(trimmed.toUpperCase())}`)
  }

  const handleAnalyze = async () => {
    const candidate = eventsQuery.data?.items.find(item => item.relatedAssets.length > 0)
    if (!candidate) return
    const response = await createAnalysis.mutateAsync({
      eventId: candidate.id,
      assetIds: candidate.relatedAssets.map(asset => asset.assetId),
    })
    navigate(`/audit/${response.data.id}`)
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
        <div className="sidebar__brand">
          <button className="icon-button" type="button" aria-label="Colapsar navegacion" onClick={() => setCollapsed(current => !current)}>
            <Menu size={18} />
          </button>
          {!collapsed ? (
            <div>
              <strong>NexoMercado AI</strong>
              <span>Track 5 backend-driven demo</span>
            </div>
          ) : null}
        </div>

        <nav className="sidebar__nav">
          {navigationItems.map(item => {
            const Icon = item.icon
            return (
              <NavLink key={item.to} className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`} to={item.to}>
                <Icon size={18} />
                {!collapsed ? <span>{item.label}</span> : null}
              </NavLink>
            )
          })}
        </nav>
      </aside>

      <div className="app-shell__main">
        <header className="topbar">
          <div className="topbar__search">
            <Search size={16} />
            <input
              aria-label="Buscar activo o senal"
              value={query}
              onChange={event => setQuery(event.target.value)}
              onKeyDown={event => {
                if (event.key === 'Enter') handleSearch()
              }}
              placeholder="Buscar simbolo o signalId"
            />
          </div>

          <div className="topbar__meta">
            {signalsQuery.data ? <DataModeBadge mode={signalsQuery.data.meta.dataMode} /> : null}
            {signalsQuery.data ? (
              <DataFreshnessIndicator asOf={signalsQuery.data.meta.dataAsOf} retrievedAt={signalsQuery.data.meta.retrievedAt} />
            ) : null}
            <AgentStatus
              status={latestRun?.status ?? 'completed'}
              currentNode={latestRun?.currentNode}
              modelName={latestRun?.modelName}
            />
            <button className="primary-button" type="button" onClick={handleAnalyze} disabled={createAnalysis.isPending || !eventsQuery.data?.items.length}>
              <Sparkles size={16} />
              {createAnalysis.isPending ? 'Lanzando analisis' : 'Nuevo analisis'}
            </button>
          </div>
        </header>

        {latestRun ? (
          <div className="status-strip">
            <span>Run reciente {compactId(latestRun.id)}</span>
            <span>{latestRun.steps.length} pasos</span>
            <span>{latestRun.currentNode}</span>
          </div>
        ) : null}

        <main className="page-container">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
