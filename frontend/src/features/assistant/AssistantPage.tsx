import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useConversationQuery,
  useCreateAnalysisMutation,
  useCreateConversationMessageMutation,
  useCreateConversationMutation,
  useEcuadorSnapshotsQuery,
  useEventsQuery,
  useRecentRunsQuery,
  useSignalsQuery,
} from '../../shared/api/queries'
import { EmptyState, SurfaceCard } from '../../shared/ui/primitives'
import { AnalysisStatusBadge } from '../../shared/ui/badges'
import { compactId } from '../../shared/lib/format'

export function AssistantPage() {
  const navigate = useNavigate()
  const [conversationId, setConversationId] = useState('')
  const [prompt, setPrompt] = useState('Explica la senal de AAPL con evidencia y contexto Ecuador.')
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const ecuadorSnapshotsQuery = useEcuadorSnapshotsQuery()
  const conversationQuery = useConversationQuery(conversationId)
  const createConversation = useCreateConversationMutation()
  const createConversationMessage = useCreateConversationMessageMutation()
  const createAnalysis = useCreateAnalysisMutation()
  const latestRun = useRecentRunsQuery().map(item => item.data).find(Boolean)

  const handleAnalyze = async () => {
    const candidate = eventsQuery.data?.items.find(item => item.relatedAssets.length > 0)
    if (!candidate) return
    const response = await createAnalysis.mutateAsync({
      eventId: candidate.id,
      assetIds: candidate.relatedAssets.map(asset => asset.assetId),
    })
    navigate(`/audit/${response.data.id}`)
  }

  const handleConversation = async () => {
    const activeConversationId =
      conversationId ||
      (
        await createConversation.mutateAsync({
          watchlistId: 'watchlist_demo_global',
        })
      ).data.id
    if (!conversationId) setConversationId(activeConversationId)
    await createConversationMessage.mutateAsync({ conversationId: activeConversationId, content: prompt })
  }

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="Asistente IA" title="Orquestacion visible y honesta">
        <p className="hero-copy">
          Conversacion persistida con contexto activo, prompts guiados y progreso real del run.
        </p>
        <div className="card-actions">
          <button className="primary-button" type="button" onClick={handleAnalyze} disabled={createAnalysis.isPending || !eventsQuery.data?.items.length}>
            {createAnalysis.isPending ? 'Arrancando run' : 'Iniciar analisis contextual'}
          </button>
          {latestRun ? (
            <button className="secondary-button" type="button" onClick={() => navigate(`/audit/${latestRun.id}`)}>
              Abrir ultimo run
            </button>
          ) : null}
        </div>
      </SurfaceCard>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Contexto disponible" title="Eventos y senales accesibles">
          {signalsQuery.data?.items.length ? (
            <ul className="text-list">
              {signalsQuery.data.items.slice(0, 5).map(signal => (
                <li key={signal.id}>
                  {signal.asset.symbol}: {signal.thesis ?? 'Sin tesis'}.
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Sin contexto aun" description="Cargando senales para alimentar el panel." />
          )}
        </SurfaceCard>

        <SurfaceCard eyebrow="Prompting guiado" title="Sugerencias para el demo">
          <ul className="text-list">
            <li>Explica la reaccion de AAPL frente al evento principal y muestra las evidencias mas fuertes.</li>
            <li>Resume por que una senal fue escalada y que investigacion adicional necesita.</li>
            <li>Compara impacto del activo contra benchmark sin fabricar cifras fuera del backend.</li>
          </ul>
        </SurfaceCard>
      </section>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Contexto Ecuador" title="Snapshots institucionales trazables">
          {ecuadorSnapshotsQuery.data?.items.length ? (
            <ul className="text-list">
              {ecuadorSnapshotsQuery.data.items.map(snapshot => (
                <li key={snapshot.id}>
                  {snapshot.sourceName}: {snapshot.title}. Hash {compactId(snapshot.contentHash)}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Sin snapshots" description="No se pudo cargar el contexto institucional." />
          )}
        </SurfaceCard>

        <SurfaceCard eyebrow="Conversacion" title={conversationId ? `Contexto ${compactId(conversationId)}` : 'Nueva conversacion'}>
          <div className="disabled-composer">
            <textarea rows={4} value={prompt} onChange={event => setPrompt(event.target.value)} />
            <button
              className="primary-button"
              disabled={!prompt.trim() || createConversation.isPending || createConversationMessage.isPending}
              type="button"
              onClick={handleConversation}
            >
              {createConversation.isPending || createConversationMessage.isPending ? 'Guardando' : 'Guardar mensaje'}
            </button>
          </div>
          {conversationQuery.data?.conversation.messages.length ? (
            <ul className="text-list">
              {conversationQuery.data.conversation.messages.map(message => (
                <li key={message.id}>
                  {message.role}: {message.content}
                </li>
              ))}
            </ul>
          ) : null}
        </SurfaceCard>
      </section>

      <SurfaceCard eyebrow="Run reciente" title="Auditoria conectada">
        <div className="disabled-composer">
          <textarea rows={4} disabled value="La conversacion queda separada del run; el analisis usa los contratos auditables del backend." />
        </div>
        {latestRun ? (
          <div className="status-strip status-strip--embedded">
            <span>Run activo {compactId(latestRun.id)}</span>
            <AnalysisStatusBadge status={latestRun.status} />
          </div>
        ) : null}
      </SurfaceCard>
    </div>
  )
}
