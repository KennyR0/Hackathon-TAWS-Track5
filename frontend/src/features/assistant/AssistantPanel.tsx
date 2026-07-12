import { ArrowRight, Sparkles, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useStartAnalysis } from '../../shared/api/useStartAnalysis'

export function AssistantPanel({ onNavigate, onClose }: { onNavigate?: () => void; onClose?: () => void }) {
  const location = useLocation()
  const analysis = useStartAnalysis()

  const startContextualAnalysis = async () => {
    await analysis.startAnalysis()
    onNavigate?.()
  }

  return (
    <section className="assistant-panel" aria-labelledby="assistant-panel-title">
      <header className="assistant-head">
        <div>
          <p className="section-eyebrow">Asistente contextual</p>
          <h2 id="assistant-panel-title">Investigación</h2>
        </div>
        {onClose ? <button className="icon-button" type="button" aria-label="Cerrar asistente" onClick={onClose}><X size={17} /></button> : null}
      </header>

      <div className="context-chip"><span>Contexto</span><strong>{location.pathname === '/summary' ? 'Panorama' : location.pathname.split('/')[1] || 'Panorama'}</strong></div>

      <div className="assistant-panel-body">
        <span>NEXO</span>
        <p>Puedo iniciar un análisis verificable del contexto disponible y llevarte a su auditoría. No genero cifras nuevas desde esta interfaz.</p>
        <button className="primary-button" type="button" onClick={() => void startContextualAnalysis()} disabled={analysis.isStarting || !analysis.canStart}>
          <Sparkles size={15} />
          {analysis.isStarting ? 'Iniciando análisis' : 'Analizar contexto'}
        </button>
      </div>

      <div className="assistant-panel-footer">
        <p>Conversación persistida y proveedores live</p>
        <Link className="assistant-link" to="/assistant" onClick={onNavigate}>
          Abrir asistente completo <ArrowRight size={15} />
        </Link>
        <small>El análisis y la conversación permanecen como flujos auditables separados.</small>
      </div>
    </section>
  )
}
