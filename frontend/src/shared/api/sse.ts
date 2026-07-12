import { getAccessToken, supabase } from '../../lib/auth'
import type { ApiSseEvent } from './contracts'
import { apiClient } from './client'

export interface SseSubscriptionOptions {
  runId: string
  lastEventId?: string | null
  onStep: (event: ApiSseEvent, lastEventId: string | null) => void
  onError?: () => void
}

export function subscribeToAnalysisStream(options: SseSubscriptionOptions): () => void {
  const controller = new AbortController()
  void consumeAnalysisStream(options, controller.signal)
  return () => controller.abort()
}

async function consumeAnalysisStream(options: SseSubscriptionOptions, signal: AbortSignal) {
  const url = new URL(`${apiClient.getApiBaseUrl()}/analyses/${options.runId}/stream`, window.location.origin)
  if (options.lastEventId) url.searchParams.set('lastEventId', options.lastEventId)
  const token = await getAccessToken()

  try {
    const response = await fetch(url, {
      signal,
      headers: {
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    if (response.status === 401 && supabase) await supabase.auth.signOut({ scope: 'local' })
    if (!response.ok || !response.body) throw new Error(`SSE HTTP ${response.status}`)

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''
    let latestEventId = options.lastEventId ?? null
    while (!signal.aborted) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const fields = Object.fromEntries(
          block
            .split('\n')
            .filter(line => line.includes(':'))
            .map(line => {
              const separator = line.indexOf(':')
              return [line.slice(0, separator), line.slice(separator + 1).trimStart()]
            }),
        )
        if (fields.id) latestEventId = fields.id
        if (fields.event === 'analysis-step' && fields.data) {
          options.onStep(JSON.parse(fields.data) as ApiSseEvent, latestEventId)
        }
      }
    }
  } catch {
    if (!signal.aborted) options.onError?.()
  }
}
