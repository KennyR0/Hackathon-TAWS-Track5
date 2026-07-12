import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Activity, Radio, FileText, ClipboardList } from 'lucide-react';
import { TRANSLATIONS } from '../../lib/translations';

type DataMode = 'fixture' | 'live' | 'fallback';

// Map de colores de acento por sección (se usa para el borde activo del sidebar)
const sectionAccentMap: Record<string, string> = {
  '/': 'border-accent-radar',
  '/signal': 'border-accent-signal',
  '/briefing': 'border-accent-briefing',
  '/audit': 'border-accent-audit',
};

export function MainLayout() {
  const [dataMode] = useState<DataMode>('fixture');
  const location = useLocation();
  
  // Determinar el color de acento activo según la ruta
  const activeAccentBorder = sectionAccentMap[location.pathname] || 'border-accent-radar';

  return (
    <div className="flex h-screen bg-bg text-text-primary font-sans antialiased">
      {/* SIDEBAR NAVEGACIÓN */}
      <aside className="w-56 border-r border-border bg-surface flex flex-col justify-between">
        <div>
          {/* Logo / Marca */}
          <div className="p-4 border-b border-border">
            <h1 className="text-[17px] font-serif font-bold tracking-tight flex items-center gap-2">
              <span className="inline-block w-2 h-2 bg-action-accent" />
              NexoMercado AI
            </h1>
            <p className="text-[10px] text-text-muted mt-1 uppercase tracking-wider font-mono">Terminal de Inteligencia</p>
          </div>

          <nav className="p-3 space-y-1">
            <NavItem to="/" icon={<Activity size={15} />} label={TRANSLATIONS.navigation.radar} accentColor="text-accent-radar" />
            <NavItem to="/signal" icon={<Radio size={15} />} label="Detalle de Señal" accentColor="text-accent-signal" />
            <NavItem to="/briefing" icon={<FileText size={15} />} label="Briefing" accentColor="text-accent-briefing" />
            <NavItem to="/audit" icon={<ClipboardList size={15} />} label={TRANSLATIONS.navigation.audit} accentColor="text-accent-audit" />
          </nav>
        </div>

        <div className="p-4 border-t border-border text-[11px] text-text-muted">
          {/* FASE 8: EXTENSIÓN AUTENTICACIÓN Y ROLES */}
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-surface-elevated border border-border flex items-center justify-center text-[10px] font-mono font-bold text-text-secondary">AD</div>
            <span className="font-mono">Analista Demo</span>
          </div>
        </div>
      </aside>

      {/* ÁREA PRINCIPAL */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* TOPBAR / HEADER — con borde de acento según la sección activa */}
        <header className={`h-12 border-b ${activeAccentBorder} bg-surface flex items-center justify-between px-6 shrink-0`}>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-[11px] font-mono text-text-secondary uppercase">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full bg-status-positive-text opacity-30"></span>
                <span className="relative inline-flex h-1.5 w-1.5 bg-status-positive-text"></span>
              </span>
              Agentes en reposo
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* INDICADOR GLOBAL DE DATAMODE */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
                Origen:
              </span>
              <span className={`px-1.5 py-0.5 text-[10px] font-mono font-bold uppercase border border-current rounded-sm ${
                dataMode === 'fixture' ? 'text-status-uncertain-text' :
                dataMode === 'live' ? 'text-status-positive-text' :
                'text-status-negative-text'
              }`}>
                {TRANSLATIONS.dataModes[dataMode]}
              </span>
            </div>
          </div>
        </header>

        {/* CONTENIDO PRINCIPAL */}
        <main className="flex-1 overflow-auto p-6 bg-bg">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

// Subcomponente de Navegación — con icono coloreado cuando activo
function NavItem({ to, icon, label, accentColor }: { to: string; icon: React.ReactNode; label: string; accentColor: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-1.5 text-[13px] font-medium transition-all duration-150 ${
          isActive 
            ? `bg-surface-elevated text-text-primary ${accentColor} border-l-2 border-current [&>svg]:!text-current` 
            : 'text-text-secondary hover:bg-surface-elevated/30 hover:text-text-primary'
        }`
      }
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}
