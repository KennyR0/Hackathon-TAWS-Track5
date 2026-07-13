import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import { mapBriefing, mapEventView, mapEvidence, mapMarketSnapshot, mapRun, mapSignal, mapWatchlist } from './mappers'
import { recentBriefingsStorage, recentRunsStorage } from './storage'
import type { ApiMeta, ApiReviewRequest, ApiSignalReview } from './contracts'
import type { EvidenceViewModel, SignalViewModel } from '../types/view-models'

interface SignalDetailQueryData {
  signal: SignalViewModel
  evidence: EvidenceViewModel[]
  reviews: ApiSignalReview[]
  meta: ApiMeta
}

export const queryKeys = {
  events: (filters?: { instrumentType?: string; asset?: string; publishedAfter?: string }) => ['events', filters] as const,
  event: (eventId: string) => ['event', eventId] as const,
  similarEvents: (eventId: string) => ['event', eventId, 'similar'] as const,
  ecuadorSnapshots: () => ['ecuador-snapshots'] as const,
  signals: () => ['signals'] as const,
  marketSnapshots: (filters?: { asset?: string; interval?: '1h' | '1d' }) => ['market-snapshots', filters] as const,
  instruments: (query?: string) => ['instruments', query ?? 'all'] as const,
  marketQuotes: (symbols: string[]) => ['market-quotes', symbols] as const,
  providerRuntime: () => ['runtime', 'providers'] as const,
  signal: (signalId: string) => ['signal', signalId] as const,
  signalEvidence: (signalId: string) => ['signal', signalId, 'evidence'] as const,
  signalReviews: (signalId: string) => ['signal', signalId, 'reviews'] as const,
  briefing: (briefingId: string) => ['briefing', briefingId] as const,
  recentBriefings: () => ['briefings', 'recent'] as const,
  run: (runId: string) => ['run', runId] as const,
  runSteps: (runId: string) => ['run', runId, 'steps'] as const,
  recentRuns: () => ['runs', 'recent'] as const,
  watchlist: () => ['watchlist', 'demo-global'] as const,
  conversation: (conversationId: string) => ['conversation', conversationId] as const,
}

export function useEventsQuery(filters?: { instrumentType?: string; asset?: string; publishedAfter?: string }) {
  return useQuery({
    queryKey: queryKeys.events(filters),
    queryFn: async () => {
      const payload = await apiClient.listEvents(filters)
      return {
        items: payload.data.map(item => mapEventView(item, payload.meta)),
        meta: payload.meta,
      }
    },
  })
}

export function useEventQuery(eventId: string) {
  return useQuery({
    queryKey: queryKeys.event(eventId),
    queryFn: async () => {
      const payload = await apiClient.getEvent(eventId)
      return mapEventView(payload.data, payload.meta)
    },
    enabled: Boolean(eventId),
  })
}

export function useSimilarEventsQuery(eventId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.similarEvents(eventId),
    queryFn: async () => {
      const payload = await apiClient.listSimilarEvents(eventId)
      return {
        items: payload.data,
        meta: payload.meta,
      }
    },
    enabled: (options?.enabled ?? true) && Boolean(eventId),
  })
}

export function useEcuadorSnapshotsQuery() {
  return useQuery({
    queryKey: queryKeys.ecuadorSnapshots(),
    queryFn: async () => {
      const payload = await apiClient.listEcuadorSnapshots()
      return {
        items: payload.data,
        meta: payload.meta,
      }
    },
  })
}

export function useSignalsQuery() {
  return useQuery({
    queryKey: queryKeys.signals(),
    queryFn: async () => {
      const payload = await apiClient.listSignals()
      return {
        items: payload.data.map(item => mapSignal(item, payload.meta)),
        meta: payload.meta,
      }
    },
  })
}

export function useMarketSnapshotsQuery(filters?: { asset?: string; interval?: '1h' | '1d' }, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.marketSnapshots(filters),
    queryFn: async () => {
      const payload = await apiClient.listMarketSnapshots(filters)
      return {
        items: payload.data.map(item => mapMarketSnapshot(item, payload.meta)),
        meta: payload.meta,
      }
    },
    enabled: options?.enabled ?? true,
  })
}

export function useInstrumentsQuery(query?: string) {
  const normalized = query?.trim() ?? ''
  return useQuery({
    queryKey: queryKeys.instruments(normalized),
    queryFn: async () => {
      const payload = await apiClient.listInstruments(normalized.length >= 2 ? { query: normalized } : undefined)
      return { items: payload.data, meta: payload.meta }
    },
    enabled: normalized.length === 0 || normalized.length >= 2,
    staleTime: 15 * 60 * 1000,
  })
}

export function useMarketQuotesQuery(symbols: string[], options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.marketQuotes(symbols),
    queryFn: async () => {
      const payload = await apiClient.listMarketQuotes(symbols)
      return { items: payload.data, meta: payload.meta }
    },
    enabled: (options?.enabled ?? true) && symbols.length > 0 && symbols.length <= 10,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}

export function useProviderRuntimeQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.providerRuntime(),
    queryFn: async () => {
      const payload = await apiClient.getProviderRuntimeStatus()
      return {
        status: payload.data,
        meta: payload.meta,
      }
    },
    enabled: options?.enabled ?? false,
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useSignalDetailQuery(signalId: string) {
  return useQuery({
    queryKey: queryKeys.signal(signalId),
    queryFn: async () => {
      const [signalPayload, evidencePayload, reviewsPayload] = await Promise.all([
        apiClient.getSignal(signalId),
        apiClient.getSignalEvidence(signalId),
        apiClient.getSignalReviews(signalId),
      ])

      return {
        signal: mapSignal(signalPayload.data, signalPayload.meta),
        evidence: evidencePayload.data.map(mapEvidence),
        reviews: reviewsPayload.data,
        meta: signalPayload.meta,
      }
    },
    enabled: Boolean(signalId),
  })
}

export function useBriefingQuery(briefingId: string) {
  return useQuery({
    queryKey: queryKeys.briefing(briefingId),
    queryFn: async () => {
      const payload = await apiClient.getBriefing(briefingId)
      return mapBriefing(payload.data, payload.meta)
    },
    enabled: Boolean(briefingId),
  })
}

export function useRecentBriefingsQuery() {
  const ids = recentBriefingsStorage.read()
  return useQueries({
    queries: ids.map(briefingId => ({
      queryKey: queryKeys.briefing(briefingId),
      queryFn: async () => {
        const payload = await apiClient.getBriefing(briefingId)
        return mapBriefing(payload.data, payload.meta)
      },
      staleTime: 10_000,
    })),
  })
}

export function useRunQuery(runId: string) {
  return useQuery({
    queryKey: queryKeys.run(runId),
    queryFn: async () => {
      const [runPayload, stepsPayload] = await Promise.all([apiClient.getAnalysis(runId), apiClient.listRunSteps(runId)])
      return mapRun(runPayload.data, stepsPayload.data, runPayload.meta)
    },
    refetchInterval: (query: { state: { data?: { status?: string } } }) => (query.state.data?.status === 'processing' ? 3_000 : false),
    enabled: Boolean(runId),
  })
}

export function useRecentRunsQuery() {
  const ids = recentRunsStorage.read()
  return useQueries({
    queries: ids.map(runId => ({
      queryKey: queryKeys.run(runId),
      queryFn: async () => {
        const [runPayload, stepsPayload] = await Promise.all([apiClient.getAnalysis(runId), apiClient.listRunSteps(runId)])
        return mapRun(runPayload.data, stepsPayload.data, runPayload.meta)
      },
      refetchInterval: (query: { state: { data?: { status?: string } } }) => (query.state.data?.status === 'processing' ? 3_000 : false),
      staleTime: 5_000,
    })),
  })
}

export function useWatchlistQuery() {
  const signalsQuery = useSignalsQuery()
  const eventsQuery = useEventsQuery()

  return useQuery({
    queryKey: queryKeys.watchlist(),
    queryFn: async () => {
      const payload = await apiClient.getWatchlist()
      const signals = signalsQuery.data?.items ?? []
      const events = eventsQuery.data?.items ?? []
      return mapWatchlist(payload.data, signals, events)
    },
    enabled: signalsQuery.isSuccess && eventsQuery.isSuccess,
  })
}

export function useConversationQuery(conversationId: string) {
  return useQuery({
    queryKey: queryKeys.conversation(conversationId),
    queryFn: async () => {
      const payload = await apiClient.getConversation(conversationId)
      return {
        conversation: payload.data,
        meta: payload.meta,
      }
    },
    enabled: Boolean(conversationId),
  })
}

export function useCreateReviewMutation(signalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ApiReviewRequest) => apiClient.createSignalReview(signalId, payload),
    onSuccess: async payload => {
      const latestReview = payload.data.at(-1)
      if (latestReview) {
        const reviewSummary = {
          status: latestReview.status,
          justification: latestReview.justification,
          reviewedBy: latestReview.reviewedBy,
          reviewedAt: latestReview.reviewedAt,
        }
        queryClient.setQueryData<SignalDetailQueryData>(queryKeys.signal(signalId), current => {
          if (!current) return current
          return {
            ...current,
            signal: {
              ...current.signal,
              reviewStatus: latestReview.status,
              reviewSummary,
              updatedAt: latestReview.createdAt,
              raw: {
                ...current.signal.raw,
                review: reviewSummary,
                updatedAt: latestReview.createdAt,
              },
            },
            reviews: payload.data,
          }
        })
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.signal(signalId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.signals() }),
      ])
    },
  })
}

export function useCreateBriefingMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: apiClient.createBriefing,
    onSuccess: async payload => {
      recentBriefingsStorage.push(payload.data.briefingId)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.signals() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.briefing(payload.data.briefingId) }),
      ])
    },
  })
}

export function useCreateAnalysisMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: apiClient.createAnalysis,
    onSuccess: async payload => {
      recentRunsStorage.push(payload.data.id)
      await queryClient.invalidateQueries({ queryKey: queryKeys.run(payload.data.id) })
    },
  })
}

export function useCreateConversationMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: apiClient.createConversation,
    onSuccess: async payload => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.conversation(payload.data.id) })
    },
  })
}

export function useCreateConversationMessageMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: { conversationId: string; content: string }) =>
      apiClient.createConversationMessage(payload.conversationId, { content: payload.content }),
    onSuccess: async (_payload, variables) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.conversation(variables.conversationId) })
    },
  })
}
