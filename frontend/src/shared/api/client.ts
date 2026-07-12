import type {
  ApiAgentRun,
  ApiAgentRunStep,
  ApiBriefing,
  ApiBriefingRequest,
  ApiError,
  ApiEventView,
  ApiEvidence,
  ApiMeta,
  ApiReviewRequest,
  ApiSignal,
  ApiSignalReview,
  ApiWatchlist,
} from './contracts'
import { getAccessToken, supabase } from '../../lib/auth'

function normalizeApiBaseUrl(rawValue?: string): string {
  const value = (rawValue?.trim() || '/api').replace(/\/$/, '')
  if (!value) return '/api'
  if (value.endsWith('/api')) return value
  if (value.startsWith('http://') || value.startsWith('https://')) return `${value}/api`
  return value
}

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL)
const API_V1_URL = `${API_BASE_URL}/v1`

interface Envelope<T> {
  data: T
  meta: ApiMeta
}

export class ApiClientError extends Error {
  readonly status: number
  readonly code?: string
  readonly requestId?: string | null

  constructor(error: ApiError, status: number) {
    super(error.message)
    this.name = 'ApiClientError'
    this.status = status
    this.code = error.code
    this.requestId = error.requestId
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const accessToken = await getAccessToken()
  const response = await fetch(`${API_V1_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401 && supabase) {
      await supabase.auth.signOut({ scope: 'local' })
    }
    const fallback = {
      code: `http_${response.status}`,
      message: `La solicitud fallo con HTTP ${response.status}.`,
      requestId: null,
    } satisfies ApiError

    try {
      const body = (await response.json()) as ApiError
      throw new ApiClientError(body, response.status)
    } catch (error) {
      if (error instanceof ApiClientError) throw error
      throw new ApiClientError(fallback, response.status)
    }
  }

  return (await response.json()) as T
}

function createIdempotencyKey(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`
}

export const apiClient = {
  getApiBaseUrl(): string {
    return API_V1_URL
  },
  listEvents(filters?: { instrumentType?: string; asset?: string; publishedAfter?: string }) {
    const params = new URLSearchParams()
    if (filters?.instrumentType && filters.instrumentType !== 'all') params.set('instrumentType', filters.instrumentType)
    if (filters?.asset) params.set('asset', filters.asset)
    if (filters?.publishedAfter) params.set('publishedAfter', filters.publishedAfter)
    const query = params.toString() ? `?${params.toString()}` : ''
    return request<Envelope<ApiEventView[]>>(`/events${query}`)
  },
  getEvent(eventId: string) {
    return request<Envelope<ApiEventView>>(`/events/${eventId}`)
  },
  listSignals() {
    return request<Envelope<ApiSignal[]>>('/signals')
  },
  getSignal(signalId: string) {
    return request<Envelope<ApiSignal>>(`/signals/${signalId}`)
  },
  getSignalEvidence(signalId: string) {
    return request<Envelope<ApiEvidence[]>>(`/signals/${signalId}/evidence`)
  },
  getSignalReviews(signalId: string) {
    return request<Envelope<ApiSignalReview[]>>(`/signals/${signalId}/reviews`)
  },
  createSignalReview(signalId: string, payload: ApiReviewRequest) {
    return request<Envelope<ApiSignalReview[]>>(`/signals/${signalId}/reviews`, {
      method: 'POST',
      headers: { 'Idempotency-Key': createIdempotencyKey(`review-${signalId}`) },
      body: JSON.stringify(payload),
    })
  },
  createBriefing(payload: ApiBriefingRequest) {
    return request<Envelope<ApiBriefing>>('/briefings', {
      method: 'POST',
      headers: { 'Idempotency-Key': createIdempotencyKey(`briefing-${payload.watchlistId}`) },
      body: JSON.stringify(payload),
    })
  },
  getBriefing(briefingId: string) {
    return request<Envelope<ApiBriefing>>(`/briefings/${briefingId}`)
  },
  createAnalysis(payload: { eventId: string; assetIds: string[] }) {
    return request<Envelope<ApiAgentRun>>('/analyses', {
      method: 'POST',
      headers: { 'Idempotency-Key': createIdempotencyKey(`analysis-${payload.eventId}`) },
      body: JSON.stringify(payload),
    })
  },
  getAnalysis(runId: string) {
    return request<Envelope<ApiAgentRun>>(`/analyses/${runId}`)
  },
  listRunSteps(runId: string) {
    return request<Envelope<ApiAgentRunStep[]>>(`/runs/${runId}/steps`)
  },
  getWatchlist() {
    return request<Envelope<ApiWatchlist>>('/watchlists/demo-global')
  },
}
