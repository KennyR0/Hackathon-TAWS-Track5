import { useNavigate } from 'react-router-dom'
import { useCreateAnalysisMutation, useEventsQuery, useRecentRunsQuery, useSignalsQuery } from '../../shared/api/queries'
import { EmptyState, SurfaceCard } from '../../shared/ui/primitives'
import { AnalysisStatusBadge } from '../../shared/ui/badges'
import { compactId } from '../../shared/lib/format'

export function AssistantPage() {
  const navigate = useNavigate()
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
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

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="Asistente IA" title="Orquestacion visible y honesta">
        <p className="hero-copy">
          Esta vista muestra contexto activo, prompts sugeridos y progreso real del run. El backend actual no expone un endpoint de chat libre,
          asi que no simulamos una conversacion falsa.
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

      <SurfaceCard eyebrow="Chat libre" title="Pendiente de soporte backend">
        <div className="disabled-composer">
          <textarea rows={4} disabled value="El backend aun no expone un endpoint conversacional libre para enviar mensajes desde esta pantalla." />
          <button className="primary-button" disabled type="button">
            Enviar no disponible
          </button>
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
