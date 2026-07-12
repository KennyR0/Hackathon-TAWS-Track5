import type { ApiSseEvent } from './contracts'
import { apiClient } from './client'

export interface SseSubscriptionOptions {
  runId: string
  lastEventId?: string | null
  onStep: (event: ApiSseEvent, lastEventId: string | null) => void
  onError?: () => void
}

export function subscribeToAnalysisStream(options: SseSubscriptionOptions): () => void {
  const url = new URL(`${apiClient.getApiBaseUrl()}/analyses/${options.runId}/stream`, window.location.origin)
  if (options.lastEventId) {
    url.searchParams.set('lastEventId', options.lastEventId)
  }

  const source = new EventSource(url)
  let latestEventId = options.lastEventId ?? null

  source.addEventListener('analysis-step', event => {
    const message = event as MessageEvent<string>
    latestEventId = message.lastEventId || latestEventId
    options.onStep(JSON.parse(message.data) as ApiSseEvent, latestEventId)
  })

  source.onerror = () => {
    options.onError?.()
  }

  return () => {
    source.close()
  }
}
