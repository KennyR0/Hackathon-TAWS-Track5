import type {
  ApiAgentRun,
  ApiAgentRunStep,
  ApiAnalysisStatus,
  ApiArticle,
  ApiAssetRelation,
  ApiBriefing,
  ApiDataMode,
  ApiEventView,
  ApiEvidence,
  ApiImpact,
  ApiReviewStatus,
  ApiSignal,
  ApiSignalReview,
  ApiSource,
  ApiWatchlist,
} from '../api/contracts'

export interface DataMetaViewModel {
  dataMode: ApiDataMode
  provider: string
  retrievedAt: string
  dataAsOf: string
  warnings: string[]
}

export interface EventViewModel {
  id: string
  title: string
  summary: string
  eventAt: string
  articles: ApiArticle[]
  sources: ApiSource[]
  relatedAssets: ApiAssetRelation[]
  mainArticle: ApiArticle | null
  independentSourceCount: number
  warnings: string[]
  meta: DataMetaViewModel
  raw: ApiEventView
}

export interface SignalViewModel {
  id: string
  eventId: string
  asset: ApiSignal['asset']
  impact: ApiImpact
  confidence: number
  analysisStatus: ApiAnalysisStatus
  reviewStatus: ApiReviewStatus
  reviewSummary: ApiSignal['review']
  thesis: string | null
  assumptions: string[]
  invalidationConditions: string[]
  suggestedResearchActions: string[]
  priceReaction: ApiSignal['priceReaction']
  priceReactionRows: Array<{
    key: 'assetReturn' | 'benchmarkReturn' | 'abnormalReturn' | 'relativeVolume'
    label: string
    value: number
  }>
  evidenceIds: string[]
  counterEvidenceIds: string[]
  createdAt: string
  updatedAt: string
  meta: DataMetaViewModel
  raw: ApiSignal
}

export interface EvidenceViewModel {
  id: string
  claim: string
  evidenceType: ApiEvidence['evidenceType']
  supportsSignal: boolean
  sourceUrl: string
  excerpt: string | null
  articleId: string | null
  sourceId: string | null
  publishedAt: string | null
  retrievedAt: string
  raw: ApiEvidence
}

export interface ReviewEntryViewModel extends ApiSignalReview {}

export interface ReviewQueueItemViewModel {
  signal: SignalViewModel
  event: EventViewModel | null
  latestReview: ReviewEntryViewModel | null
  blockingReason: string | null
}

export interface BriefingViewModel {
  id: string
  status: ApiBriefing['status']
  createdAt: string
  updatedAt: string
  executiveSummary: string
  watchlist: ApiBriefing['watchlist']
  prioritizedSignals: ApiBriefing['prioritizedSignals']
  humanReviewSummary: ApiBriefing['humanReviewSummary']
  reviewTasks: ApiBriefing['reviewTasks']
  meta: DataMetaViewModel
  raw: ApiBriefing
}

export interface AssetSummaryViewModel {
  symbol: string
  name: string
  instrumentType: SignalViewModel['asset']['instrumentType']
  signalCount: number
  eventCount: number
  averageConfidence: number
  latestSignal: SignalViewModel | null
  signals: SignalViewModel[]
  relatedEvents: EventViewModel[]
}

export interface RunStepViewModel extends ApiAgentRunStep {}

export interface RunViewModel {
  id: string
  status: ApiAgentRun['status']
  currentNode: string
  modelName: string | null
  promptVersion: string | null
  startedAt: string
  finishedAt: string | null
  retryCount: number
  warnings: string[]
  meta: DataMetaViewModel
  steps: RunStepViewModel[]
  raw: ApiAgentRun
}

export interface WatchlistViewModel extends ApiWatchlist {
  signals: SignalViewModel[]
  assets: AssetSummaryViewModel[]
}
