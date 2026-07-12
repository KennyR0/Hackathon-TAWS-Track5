import { Bot, Menu, PanelRight, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { AssistantPanel } from '../../features/assistant/AssistantPanel'
import { GlobalSearch } from './GlobalSearch'
import { mobileNavigationItems, navigationSections } from './navigation'
import { ThemeToggle } from './ThemeToggle'

export function AppShell() {
  const [navOpen, setNavOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(true)
  const [assistantDialogOpen, setAssistantDialogOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 720px)').matches)

  useEffect(() => {
    const media = window.matchMedia('(max-width: 720px)')
    const handleChange = (event: MediaQueryListEvent) => setIsMobile(event.matches)
    media.addEventListener('change', handleChange)
    return () => media.removeEventListener('change', handleChange)
  }, [])

  useEffect(() => {
    if (!navOpen && !assistantDialogOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setNavOpen(false)
        setAssistantDialogOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [assistantDialogOpen, navOpen])

  return (
    <div className={`prototype-shell ${assistantOpen ? 'has-assistant' : ''}`}>
      <a className="skip-link" href="#main-content">Saltar al contenido</a>

      <header className="topbar">
        <button className="icon-button mobile-menu-button" type="button" aria-label="Abrir navegación" onClick={() => setNavOpen(true)}>
          <Menu size={18} />
        </button>
        <NavLink className="topbar-brand" to="/summary" aria-label="Ir a Panorama">
          <span className="brand-mark">N</span>
        </NavLink>
        <GlobalSearch />
        <div className="topbar-actions">
          <ThemeToggle />
          <button
            className={`icon-button topbar-action desktop-assistant-toggle ${assistantOpen ? 'is-active' : ''}`}
            type="button"
            aria-label={assistantOpen ? 'Cerrar asistente contextual' : 'Abrir asistente contextual'}
            aria-pressed={assistantOpen}
            onClick={() => setAssistantOpen(value => !value)}
          >
            <PanelRight size={17} />
          </button>
          <button className="avatar-button" type="button" aria-label="Perfil de Analista Demo">AD</button>
        </div>
      </header>

      <aside
        className={`sidebar ${navOpen ? 'is-open' : ''}`}
        aria-label="Navegación principal"
        aria-hidden={isMobile && !navOpen}
        inert={isMobile && !navOpen}
      >
        <div className="sidebar-brand">
          <NavLink to="/summary" onClick={() => setNavOpen(false)}>
            <span className="brand-mark">N</span>
            <span><strong>NexoMercado</strong><small>FINANCE · INTELIGENCIA</small></span>
          </NavLink>
          <button className="icon-button sidebar-close" type="button" aria-label="Cerrar navegación" onClick={() => setNavOpen(false)}>
            <X size={18} />
          </button>
        </div>
        <nav className="sidebar-nav">
          {navigationSections.map(section => (
            <section key={section.label}>
              <p>{section.label}</p>
              {section.items.map(item => (
                <NavLink key={item.to} to={item.to} onClick={() => setNavOpen(false)} className={({ isActive }) => isActive ? 'nav-item is-active' : 'nav-item'}>
                  <span>{item.number}</span>
                  <strong>{item.label}</strong>
                </NavLink>
              ))}
            </section>
          ))}
        </nav>
        <div className="sidebar-status">
          <span>BACKEND</span>
          <p>Contratos OpenAPI</p>
          <p>Datos trazables</p>
        </div>
      </aside>

      {navOpen ? <button className="nav-backdrop" type="button" aria-label="Cerrar navegación" onClick={() => setNavOpen(false)} /> : null}

      <main id="main-content" className="main-content" tabIndex={-1}>
        <Outlet />
      </main>

      {assistantOpen ? (
        <aside className="assistant-rail" aria-label="Asistente contextual">
          <AssistantPanel onClose={() => setAssistantOpen(false)} />
        </aside>
      ) : null}

      <button className="assistant-drawer-trigger" type="button" onClick={() => setAssistantDialogOpen(true)} aria-controls="assistant-dialog">
        <Bot size={17} />
        <span>Asistente</span>
      </button>

      {assistantDialogOpen ? (
        <div className="dialog-backdrop" onMouseDown={() => setAssistantDialogOpen(false)}>
          <section
            id="assistant-dialog"
            className="assistant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="assistant-panel-title"
            onMouseDown={event => event.stopPropagation()}
          >
            <AssistantPanel onClose={() => setAssistantDialogOpen(false)} onNavigate={() => setAssistantDialogOpen(false)} />
          </section>
        </div>
      ) : null}

      <nav className="mobile-navigation" aria-label="Navegación móvil">
        {mobileNavigationItems.map(item => {
          const Icon = item.icon
          return (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'is-active' : undefined}>
              <span>{item.number}</span>
              <Icon size={16} aria-hidden="true" />
              <small>{item.label}</small>
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
