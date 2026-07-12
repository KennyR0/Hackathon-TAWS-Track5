import { Bot, Sparkles, XCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useRecentRunsQuery, useSignalsQuery } from '../../shared/api/queries'
import { useStartAnalysis } from '../../shared/api/useStartAnalysis'
import { AnalysisStatusBadge } from '../../shared/ui/badges'
import { EmptyState } from '../../shared/ui/primitives'
import { compactId } from '../../shared/lib/format'

export function AssistantPanel({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate()
  const signalsQuery = useSignalsQuery()
  const latestRun = useRecentRunsQuery().map(item => item.data).find(Boolean)
  const analysis = useStartAnalysis()

  const openLatestRun = () => {
    if (!latestRun) return
    navigate(`/audit/${latestRun.id}`)
    onNavigate?.()
  }

  const startContextualAnalysis = async () => {
    await analysis.startAnalysis()
    onNavigate?.()
  }

  return (
    <section className="assistant-panel" aria-labelledby="assistant-panel-title">
      <header className="assistant-panel__header">
        <div>
          <p className="section-eyebrow">Asistente financiero</p>
          <h2 id="assistant-panel-title">Investigacion IA</h2>
        </div>
        <Bot size={18} aria-hidden="true" />
      </header>

      <p className="assistant-panel__copy">
        Contexto activo y progreso real del workflow. Chat libre pendiente de soporte backend.
      </p>

      <div className="assistant-panel__actions">
        <button
          className="primary-button"
          type="button"
          onClick={() => {
            void startContextualAnalysis()
          }}
          disabled={analysis.isStarting || !analysis.canStart}
        >
          <Sparkles size={15} />
          {analysis.isStarting ? 'Arrancando run' : 'Iniciar analisis'}
        </button>
        {latestRun ? (
          <button className="secondary-button" type="button" onClick={openLatestRun}>
            Abrir ultimo run
          </button>
        ) : null}
      </div>

      <section className="assistant-panel__section" aria-label="Estado operativo">
        <div className="assistant-panel__section-header">
          <span>Run</span>
          {latestRun ? <AnalysisStatusBadge status={latestRun.status} /> : <span className="muted-pill">Sin ejecucion</span>}
        </div>
        {latestRun ? (
          <div className="assistant-run-summary">
            <span>Run {compactId(latestRun.id)}</span>
            <span>{latestRun.steps.length} pasos</span>
            <span>{latestRun.currentNode}</span>
          </div>
        ) : (
          <p className="inline-hint">Inicia un analisis para ver progreso y auditoria del agente.</p>
        )}
      </section>

      <section className="assistant-panel__section" aria-label="Contexto disponible">
        <div className="assistant-panel__section-header">
          <span>Contexto</span>
        </div>
        {signalsQuery.data?.items.length ? (
          <ul className="assistant-context-list">
            {signalsQuery.data.items.slice(0, 4).map(signal => (
              <li key={signal.id}>
                <strong>{signal.asset.symbol}</strong>
                <span>{signal.thesis ?? 'Sin tesis sintetizada.'}</span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="Sin contexto aun" description="Cargando senales verificables para alimentar el panel." />
        )}
      </section>

      <section className="assistant-panel__section" aria-label="Prompts sugeridos">
        <div className="assistant-panel__section-header">
          <span>Prompts sugeridos</span>
        </div>
        <ul className="assistant-prompt-list">
          <li>Explica la reaccion de AAPL frente al evento principal.</li>
          <li>Resume por que una senal fue escalada.</li>
          <li>Compara impacto del activo contra benchmark sin fabricar cifras.</li>
        </ul>
      </section>

      <section className="assistant-panel__section" aria-label="Chat libre no disponible">
        <div className="assistant-panel__section-header">
          <span>Chat libre</span>
          <XCircle size={15} aria-hidden="true" />
        </div>
        <div className="disabled-composer">
          <textarea
            rows={3}
            disabled
            readOnly
            value="El backend aun no expone un endpoint conversacional libre para enviar mensajes desde esta pantalla."
          />
          <button className="primary-button" disabled type="button">
            Enviar no disponible
          </button>
        </div>
      </section>
    </section>
  )
}
