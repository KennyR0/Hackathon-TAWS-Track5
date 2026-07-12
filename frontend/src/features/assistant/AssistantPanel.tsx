import { ArrowUp, Mic, Plus, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useStartAnalysis } from '../../shared/api/useStartAnalysis'

export function AssistantPanel({ onNavigate }: { onNavigate?: () => void }) {
  const [draft, setDraft] = useState('')
  const analysis = useStartAnalysis()

  const startContextualAnalysis = async () => {
    await analysis.startAnalysis()
    onNavigate?.()
  }

  return (
    <section className="assistant-panel" aria-labelledby="assistant-panel-title">
      <header className="assistant-panel__header">
        <div>
          <p className="section-eyebrow">Asistente financiero</p>
          <h2 id="assistant-panel-title">Investigación</h2>
        </div>
      </header>

      <div className="assistant-panel__body">
        <p className="assistant-panel__greeting">Hola. Haz cualquier pregunta sobre finanzas.</p>
        <p className="assistant-panel__copy">El chat libre esta preparado en interfaz y pendiente de endpoint conversacional.</p>

        <button
          className="primary-button assistant-panel__analysis-button"
          type="button"
          onClick={() => {
            void startContextualAnalysis()
          }}
          disabled={analysis.isStarting || !analysis.canStart}
        >
          <Sparkles size={15} />
          {analysis.isStarting ? 'Arrancando análisis' : 'Iniciar análisis'}
        </button>
      </div>

      <form
        className="assistant-composer"
        aria-label="Chat libre"
        onSubmit={event => {
          event.preventDefault()
        }}
      >
        <label className="sr-only" htmlFor="assistant-message">
          Hacer pregunta
        </label>
        <textarea
          id="assistant-message"
          value={draft}
          onChange={event => setDraft(event.target.value)}
          placeholder="Hacer pregunta"
          rows={4}
        />
        <div className="assistant-composer__footer">
          <button className="icon-button" type="button" aria-label="Adjuntar contexto" disabled>
            <Plus size={17} />
          </button>
          <div className="assistant-composer__actions">
            <button className="icon-button" type="button" aria-label="Dictar pregunta" disabled>
              <Mic size={17} />
            </button>
            <button className="icon-button assistant-composer__send" type="submit" aria-label="Enviar pregunta" disabled>
              <ArrowUp size={17} />
            </button>
          </div>
        </div>
        <p className="assistant-composer__status">Envío no disponible hasta conectar el endpoint de chat libre.</p>
      </form>
    </section>
  )
}
