import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import { mapBriefing, mapEventView, mapEvidence, mapRun, mapSignal, mapWatchlist } from './mappers'
import { recentBriefingsStorage, recentRunsStorage } from './storage'
import type { ApiReviewRequest } from './contracts'

export const queryKeys = {
  events: (filters?: { instrumentType?: string; asset?: string; publishedAfter?: string }) => ['events', filters] as const,
  event: (eventId: string) => ['event', eventId] as const,
  signals: () => ['signals'] as const,
  signal: (signalId: string) => ['signal', signalId] as const,
  signalEvidence: (signalId: string) => ['signal', signalId, 'evidence'] as const,
  signalReviews: (signalId: string) => ['signal', signalId, 'reviews'] as const,
  briefing: (briefingId: string) => ['briefing', briefingId] as const,
  recentBriefings: () => ['briefings', 'recent'] as const,
  run: (runId: string) => ['run', runId] as const,
  runSteps: (runId: string) => ['run', runId, 'steps'] as const,
  recentRuns: () => ['runs', 'recent'] as const,
  watchlist: () => ['watchlist', 'demo-global'] as const,
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

export function useCreateReviewMutation(signalId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ApiReviewRequest) => apiClient.createSignalReview(signalId, payload),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.signal(signalId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.signalReviews(signalId) }),
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
