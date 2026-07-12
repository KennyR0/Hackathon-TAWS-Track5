import { useNavigate } from 'react-router-dom'
import { useCreateAnalysisMutation, useEventsQuery } from './queries'
import type { EventViewModel } from '../types/view-models'

export function useStartAnalysis(candidateEvents?: EventViewModel[]) {
  const navigate = useNavigate()
  const eventsQuery = useEventsQuery()
  const createAnalysis = useCreateAnalysisMutation()
  const events = candidateEvents ?? eventsQuery.data?.items ?? []
  const candidate = events.find(event => event.relatedAssets.length > 0) ?? null

  const startAnalysis = async () => {
    if (!candidate) return
    const response = await createAnalysis.mutateAsync({
      eventId: candidate.id,
      assetIds: candidate.relatedAssets.map(asset => asset.assetId),
    })
    navigate(`/audit/${response.data.id}`)
  }

  return {
    startAnalysis,
    isStarting: createAnalysis.isPending,
    canStart: Boolean(candidate),
    candidate,
  }
}
