import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useConversationQuery,
  useCreateAnalysisMutation,
  useCreateConversationResponseMutation,
  useCreateConversationMutation,
  useEcuadorSnapshotsQuery,
  useEventsQuery,
  useProviderRuntimeQuery,
  useRecentRunsQuery,
  useSignalsQuery,
} from '../../shared/api/queries'
import type {
  ApiConversationAssetContext,
  ApiConversationMessage,
  ApiDataMode,
  ApiProviderRuntimeCheck,
} from '../../shared/api/contracts'
import { AnalysisStatusBadge, DataModeBadge, WarningList } from '../../shared/ui/badges'
import { EmptyState, ErrorState, LoadingSkeleton, SurfaceCard } from '../../shared/ui/primitives'
import { compactId, formatCurrency, formatDateTime, toSentenceCase } from '../../shared/lib/format'

function providerValue(check: ApiProviderRuntimeCheck): string {
  const metrics = check.metrics
  if (check.key === 'news' && typeof metrics.articleCount === 'number') {
    return `${metrics.articleCount} noticia${metrics.articleCount === 1 ? '' : 's'}`
  }
  if (check.key === 'aapl' && (typeof metrics.close === 'string' || typeof metrics.close === 'number')) {
    return formatCurrency(Number(metrics.close), typeof metrics.currency === 'string' ? metrics.currency : 'USD')
  }
  if (check.key === 'spy' && typeof metrics.current === 'number') {
    return formatCurrency(metrics.current)
  }
  if (check.key === 'btc' && typeof metrics.usd === 'number') {
    return formatCurrency(metrics.usd)
  }
  if (check.key === 'wti' && (typeof metrics.value === 'string' || typeof metrics.value === 'number')) {
    return `${formatCurrency(Number(metrics.value))} / barril`
  }
  if (typeof metrics.error === 'string') return metrics.error
  return 'Sin dato live disponible'
}

function messageDataMode(message: ApiConversationMessage): ApiDataMode | null {
  const value = message.metadata?.dataMode
  return value === 'fixture' || value === 'live' || value === 'fallback' ? value : null
}

const suggestedPrompts = [
  { label: 'Apple', content: 'Explica la señal de Apple con evidencia y contexto Ecuador.' },
  { label: 'Bitcoin', content: 'Explica Bitcoin con evidencia y señala qué podría invalidar la tesis.' },
  { label: 'Petróleo WTI', content: 'Resume la señal del petróleo WTI y su contexto verificable.' },
  { label: 'Microsoft', content: '¿Qué datos verificados tiene NexoMercado sobre Microsoft?' },
]

function contextFromMessage(message: ApiConversationMessage | undefined): ApiConversationAssetContext | null {
  const metadata = message?.metadata
  const symbol = metadata?.assetSymbol
  const name = metadata?.assetName
  const coverage = metadata?.coverage
  const dataMode = metadata?.quoteDataMode
  if (
    typeof symbol !== 'string' ||
    typeof name !== 'string' ||
    (coverage !== 'signal' && coverage !== 'quote_only' && coverage !== 'unsupported')
  ) {
    return null
  }
  return {
    symbol,
    name,
    coverage,
    dataMode: dataMode === 'live' || dataMode === 'fallback' ? dataMode : null,
  }
}

export function AssistantPage() {
  const navigate = useNavigate()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [conversationId, setConversationId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [conversationContext, setConversationContext] = useState<ApiConversationAssetContext | null>(null)
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const ecuadorSnapshotsQuery = useEcuadorSnapshotsQuery()
  const providerRuntimeQuery = useProviderRuntimeQuery()
  const conversationQuery = useConversationQuery(conversationId)
  const createConversation = useCreateConversationMutation()
  const createConversationResponse = useCreateConversationResponseMutation()
  const createAnalysis = useCreateAnalysisMutation()
  const latestRun = useRecentRunsQuery().map(item => item.data).find(Boolean)
  const isConversationPending = createConversation.isPending || createConversationResponse.isPending
  const lastAssistantMessage = [...(conversationQuery.data?.conversation.messages ?? [])]
    .reverse()
    .find(message => message.role === 'assistant')
  const activeContext = conversationContext ?? contextFromMessage(lastAssistantMessage)

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
    createConversation.reset()
    createConversationResponse.reset()
    try {
      const activeConversationId =
        conversationId ||
        (
          await createConversation.mutateAsync({
            watchlistId: 'watchlist_demo_global',
          })
        ).data.id
      if (!conversationId) setConversationId(activeConversationId)
      const response = await createConversationResponse.mutateAsync({ conversationId: activeConversationId, content: prompt.trim() })
      setConversationContext(response.data.context)
      setPrompt('')
    } catch {
      // Mutation state renders a visible error and keeps the prompt for retry.
    }
  }

  const conversationError = createConversation.error ?? createConversationResponse.error

  const handleSuggestion = (content: string) => {
    setPrompt(content)
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  const handleNewConversation = () => {
    setConversationId('')
    setConversationContext(null)
    setPrompt('')
    createConversation.reset()
    createConversationResponse.reset()
    requestAnimationFrame(() => textareaRef.current?.focus())
  }

  return (
    <div className="page-stack">
      <SurfaceCard eyebrow="Asistente" title="Investiga con el contexto visible" className="assistant-page-intro">
        <p className="hero-copy">
          Conversación persistida con contexto activo, prompts guiados y progreso real del run.
        </p>
        <div className="card-actions">
          <button className="primary-button" type="button" onClick={handleAnalyze} disabled={createAnalysis.isPending || !eventsQuery.data?.items.length}>
            {createAnalysis.isPending ? 'Arrancando run' : 'Iniciar análisis contextual'}
          </button>
          {latestRun ? (
            <button className="secondary-button" type="button" onClick={() => navigate(`/audit/${latestRun.id}`)}>
              Abrir ultimo run
            </button>
          ) : null}
        </div>
      </SurfaceCard>

      <SurfaceCard
        eyebrow="APIs externas"
        title="Verificación en vivo"
        action={
          <button
            className="secondary-button"
            type="button"
            disabled={providerRuntimeQuery.isFetching}
            onClick={() => void providerRuntimeQuery.refetch()}
          >
            {providerRuntimeQuery.isFetching ? 'Consultando APIs' : 'Consultar APIs ahora'}
          </button>
        }
      >
        <p className="hero-copy provider-runtime-copy">
          Consulta bajo demanda. Cada resultado conserva proveedor, frescura y degradación sin alterar los snapshots históricos de las señales.
        </p>
        {providerRuntimeQuery.isFetching && !providerRuntimeQuery.data ? <LoadingSkeleton rows={3} /> : null}
        {providerRuntimeQuery.isError ? (
          <ErrorState
            title="No se pudo completar la verificacion"
            description="El backend no devolvio un estado auditable de los proveedores."
            action={
              <button className="secondary-button" type="button" onClick={() => void providerRuntimeQuery.refetch()}>
                Reintentar
              </button>
            }
          />
        ) : null}
        {!providerRuntimeQuery.data && !providerRuntimeQuery.isFetching && !providerRuntimeQuery.isError ? (
          <EmptyState
            title="Consulta aun no ejecutada"
            description="Usa el boton para consumir GDELT, Twelve Data, Finnhub, CoinGecko y FRED desde el backend."
          />
        ) : null}
        {providerRuntimeQuery.data ? (
          <div className="provider-runtime">
            <div className="status-strip status-strip--embedded">
              <span>
                Modo configurado: <strong>{providerRuntimeQuery.data.status.configuredMode}</strong>
              </span>
              <DataModeBadge mode={providerRuntimeQuery.data.status.effectiveDataMode} />
              <span>
                {providerRuntimeQuery.data.status.requestsUsed} nuevas / {providerRuntimeQuery.data.status.requestBudget} máximo
              </span>
            </div>
            <div className="provider-grid">
              {providerRuntimeQuery.data.status.checks.map(check => (
                <article className="provider-card" key={check.key}>
                  <div className="provider-card__heading">
                    <div>
                      <span>{check.provider}</span>
                      <strong>{check.resource}</strong>
                    </div>
                    <DataModeBadge mode={check.dataMode} />
                  </div>
                  <p className="provider-card__value">{providerValue(check)}</p>
                  <small>{check.dataAsOf ? `Dato: ${formatDateTime(check.dataAsOf)}` : 'Sin fecha live confirmada'}</small>
                  {check.warnings.length ? (
                    <WarningList warnings={check.warnings.map(toSentenceCase)} />
                  ) : null}
                </article>
              ))}
            </div>
            <p className="inline-hint">
              Verificado {formatDateTime(providerRuntimeQuery.data.status.checkedAt)} · Un fallback individual no se presenta como dato live.
            </p>
          </div>
        ) : null}
      </SurfaceCard>

      <section className="content-grid content-grid--wide">
        <SurfaceCard eyebrow="Contexto disponible" title="Eventos y señales accesibles">
          {signalsQuery.data?.items.length ? (
            <ul className="text-list">
              {signalsQuery.data.items.slice(0, 5).map(signal => (
                <li key={signal.id}>
                  {signal.asset.symbol}: {signal.thesis ?? 'Sin tesis'}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="Sin contexto aún" description="Cargando señales para alimentar el panel." />
          )}
        </SurfaceCard>

        <SurfaceCard eyebrow="Prompting guiado" title="Sugerencias para la presentación">
          <ul className="text-list">
            <li>Explica la reacción de AAPL frente al evento principal y muestra las evidencias más fuertes.</li>
            <li>Resume por qué una señal fue escalada y qué investigación adicional necesita.</li>
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

        <SurfaceCard
          eyebrow="Conversación"
          title={conversationId ? `Contexto ${compactId(conversationId)}` : 'Nueva conversación'}
          action={conversationId ? (
            <button className="secondary-button" type="button" onClick={handleNewConversation} disabled={isConversationPending}>
              Nueva conversación
            </button>
          ) : null}
        >
          {activeContext ? (
            <div className="conversation-context" aria-label="Instrumento activo">
              <div>
                <span>Instrumento activo</span>
                <strong>{activeContext.name} ({activeContext.symbol})</strong>
              </div>
              <div className="conversation-context__badges">
                <span className={`coverage-badge coverage-badge--${activeContext.coverage}`}>
                  {activeContext.coverage === 'signal' ? 'Señal + evidencia' : activeContext.coverage === 'quote_only' ? 'Solo datos verificados' : 'No cubierto'}
                </span>
                {activeContext.dataMode ? <DataModeBadge mode={activeContext.dataMode} /> : null}
              </div>
            </div>
          ) : null}
          <div className="conversation-suggestions" aria-label="Preguntas sugeridas">
            {suggestedPrompts.map(suggestion => (
              <button
                className="suggestion-chip"
                type="button"
                key={suggestion.label}
                onClick={() => handleSuggestion(suggestion.content)}
                disabled={isConversationPending}
              >
                {suggestion.label}
              </button>
            ))}
          </div>
          <div className="conversation-composer">
            <textarea
              ref={textareaRef}
              aria-label="Mensaje para el asistente"
              placeholder="Pregunta por cualquiera de los 25 instrumentos…"
              rows={4}
              value={prompt}
              disabled={isConversationPending}
              onChange={event => setPrompt(event.target.value)}
            />
            <button
              className="primary-button"
              disabled={!prompt.trim() || isConversationPending}
              type="button"
              onClick={handleConversation}
            >
              {isConversationPending ? 'Analizando evidencia…' : 'Enviar'}
            </button>
          </div>
          {conversationError ? (
            <p className="field-error" role="alert">
              {conversationError instanceof Error ? conversationError.message : 'No se pudo generar la respuesta.'}
            </p>
          ) : null}
          {conversationQuery.data?.conversation.messages.length ? (
            <ul className="conversation-thread" aria-live="polite">
              {conversationQuery.data.conversation.messages.map(message => (
                <li className={`conversation-message conversation-message--${message.role}`} key={message.id}>
                  <div className="conversation-message__header">
                    <strong>{message.role === 'assistant' ? 'Analista IA' : 'Tú'}</strong>
                    {messageDataMode(message) ? <DataModeBadge mode={messageDataMode(message)!} /> : null}
                  </div>
                  <p>{message.content}</p>
                  {typeof message.metadata?.warning === 'string' ? <small>{message.metadata.warning}</small> : null}
                </li>
              ))}
            </ul>
          ) : conversationId && conversationQuery.isLoading ? <LoadingSkeleton rows={2} /> : null}
        </SurfaceCard>
      </section>

      <SurfaceCard eyebrow="Run reciente" title="Auditoria conectada">
        <div className="disabled-composer">
          <textarea rows={4} disabled value="La conversación queda separada del run; el análisis usa los contratos auditables del backend." />
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
