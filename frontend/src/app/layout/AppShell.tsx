import { Bot, Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { navigationItems } from './navigation'
import { AssistantPanel } from '../../features/assistant/AssistantPanel'

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)

  useEffect(() => {
    if (!assistantOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setAssistantOpen(false)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [assistantOpen])

  return (
    <div className={`app-shell ${collapsed ? 'app-shell--collapsed' : ''}`}>
      <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}>
        <div className="sidebar__brand">
          <button
            className="icon-button"
            type="button"
            aria-label={collapsed ? 'Expandir navegacion' : 'Colapsar navegacion'}
            aria-expanded={!collapsed}
            onClick={() => setCollapsed(current => !current)}
          >
            <Menu size={18} />
          </button>
          {!collapsed ? (
            <div>
              <strong>NexoMercado AI</strong>
              <span>Track 5 backend-driven demo</span>
            </div>
          ) : null}
        </div>

        <nav className="sidebar__nav" aria-label="Navegacion principal">
          {navigationItems.map(item => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                className={({ isActive }) => `nav-link ${isActive ? 'nav-link--active' : ''}`}
                to={item.to}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={18} />
                {!collapsed ? <span>{item.label}</span> : null}
              </NavLink>
            )
          })}
        </nav>
      </aside>

      <div className="app-shell__main">
        <main className="page-container">
          <Outlet />
        </main>
      </div>

      <aside className="assistant-rail" aria-label="Asistente financiero permanente">
        <AssistantPanel />
      </aside>

      <button className="assistant-drawer-trigger" type="button" onClick={() => setAssistantOpen(true)} aria-controls="assistant-drawer">
        <Bot size={18} />
        <span>Asistente</span>
      </button>

      {assistantOpen ? (
        <div className="assistant-drawer-backdrop" onClick={() => setAssistantOpen(false)}>
          <section
            id="assistant-drawer"
            className="assistant-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="assistant-panel-title"
            onClick={event => event.stopPropagation()}
          >
            <button className="icon-button assistant-drawer__close" type="button" onClick={() => setAssistantOpen(false)} aria-label="Cerrar asistente">
              <X size={18} />
            </button>
            <AssistantPanel onNavigate={() => setAssistantOpen(false)} />
          </section>
        </div>
      ) : null}
    </div>
  )
}
