import type {
  ApiAgentRun,
  ApiAgentRunStep,
  ApiBriefing,
  ApiEventView,
  ApiEvidence,
  ApiInstrumentType,
  ApiMarketSnapshot,
  ApiMeta,
  ApiSignal,
  ApiSignalReview,
  ApiWatchlist,
} from './contracts'
import type {
  AssetSummaryViewModel,
  BriefingViewModel,
  DataMetaViewModel,
  EventViewModel,
  EvidenceViewModel,
  MarketAssetViewModel,
  MarketSnapshotViewModel,
  ReviewQueueItemViewModel,
  RunViewModel,
  SignalViewModel,
  WatchlistViewModel,
} from '../types/view-models'
import { isArticleLinkable, isEvidenceLinkable } from '../lib/news'

export function mapMeta(meta?: ApiMeta): DataMetaViewModel {
  return {
    dataMode: meta?.dataMode ?? 'fixture',
    provider: meta?.provider ?? 'fixture',
    retrievedAt: meta?.retrievedAt ?? new Date().toISOString(),
    dataAsOf: meta?.dataAsOf ?? new Date().toISOString(),
    warnings: meta?.warnings ?? [],
  }
}

function symbolFromAssetId(assetId: string): string {
  return assetId
    .replace(/^ast_/, '')
    .replace(/_usd$/i, '-USD')
    .replaceAll('_', '-')
    .toUpperCase()
}

function instrumentTypeFromRelationship(relationship: string | undefined): ApiInstrumentType {
  if (relationship === 'commodity') return 'commodity'
  if (relationship === 'macro') return 'macro'
  if (relationship === 'credit') return 'credit'
  if (relationship === 'direct' || relationship === 'sector' || relationship === 'competitor' || relationship === 'supply_chain') return 'equity'
  return 'other'
}

export function mapEventView(view: ApiEventView, meta?: ApiMeta): EventViewModel {
  const independentSourceCount = view.sources.filter(source => !source.isAggregator).length
  const mainArticle =
    view.articles.find(article => article.id === view.event.articleIds[0]) ??
    view.articles.toSorted((left, right) => left.publishedAt.localeCompare(right.publishedAt))[0] ??
    null

  return {
    id: view.event.id,
    title: view.event.title,
    summary: view.event.summary,
    eventAt: view.event.eventAt,
    articles: view.articles,
    sources: view.sources,
    relatedAssets: view.event.relatedAssets,
    mainArticle,
    mainArticleLinkable: mainArticle ? isArticleLinkable(mainArticle) : false,
    independentSourceCount,
    warnings: [...view.event.warnings, ...mapMeta(meta).warnings],
    meta: mapMeta(meta),
    raw: view,
  }
}

export function mapMarketSnapshot(snapshot: ApiMarketSnapshot, meta?: ApiMeta): MarketSnapshotViewModel {
  return {
    id: snapshot.id,
    assetId: snapshot.assetId,
    interval: snapshot.interval,
    currency: snapshot.currency,
    dataAsOf: snapshot.dataAsOf,
    retrievedAt: snapshot.retrievedAt,
    sourceUrl: snapshot.sourceUrl,
    observations: snapshot.observations.map(point => ({
      timestamp: point.timestamp,
      close: point.close,
      volume: point.volume ?? null,
    })),
    meta: mapMeta(meta),
    raw: snapshot,
  }
}

export function mapSignal(signal: ApiSignal, meta?: ApiMeta): SignalViewModel {
  const priceReactionRows = [
    { key: 'assetReturn', label: 'Activo', value: signal.priceReaction?.assetReturn ?? 0 },
    { key: 'benchmarkReturn', label: 'Benchmark', value: signal.priceReaction?.benchmarkReturn ?? 0 },
    { key: 'abnormalReturn', label: 'Retorno anormal', value: signal.priceReaction?.abnormalReturn ?? 0 },
    { key: 'relativeVolume', label: 'Volumen relativo', value: signal.priceReaction?.relativeVolume ?? 0 },
  ] as const

  return {
    id: signal.id,
    eventId: signal.eventId,
    asset: signal.asset,
    impact: signal.impact,
    confidence: signal.confidence,
    analysisStatus: signal.analysisStatus,
    reviewStatus: signal.review.status,
    reviewSummary: signal.review,
    thesis: signal.thesis,
    assumptions: signal.assumptions,
    invalidationConditions: signal.invalidationConditions,
    suggestedResearchActions: signal.suggestedResearchActions,
    disclaimer: signal.disclaimer,
    priceReaction: signal.priceReaction,
    priceReactionRows: priceReactionRows.filter(row => Number.isFinite(row.value)),
    evidenceIds: signal.evidenceIds,
    counterEvidenceIds: signal.counterEvidenceIds,
    createdAt: signal.createdAt,
    updatedAt: signal.updatedAt,
    meta: mapMeta(meta),
    raw: signal,
  }
}

export function deriveMarketAssets(
  snapshots: MarketSnapshotViewModel[],
  signals: SignalViewModel[],
  events: EventViewModel[],
): MarketAssetViewModel[] {
  const eventRelations = events.flatMap(event => event.relatedAssets.map(relation => ({ event, relation })))
  const signalBySymbol = new Map<string, SignalViewModel[]>()
  for (const signal of signals) {
    const bucket = signalBySymbol.get(signal.asset.symbol) ?? []
    bucket.push(signal)
    signalBySymbol.set(signal.asset.symbol, bucket)
  }

  return snapshots
    .map(snapshot => {
      const relation = eventRelations.find(item => item.relation.assetId === snapshot.assetId)
      const symbol = relation?.relation.symbol ?? symbolFromAssetId(snapshot.assetId)
      const matchingSignals = (signalBySymbol.get(symbol) ?? []).toSorted((left, right) => right.updatedAt.localeCompare(left.updatedAt))
      const latestSignal = matchingSignals[0] ?? null
      const relatedEvents = eventRelations.filter(item => item.relation.assetId === snapshot.assetId).map(item => item.event)
      const observations = snapshot.observations
      const first = observations[0]?.close ?? null
      const last = observations.at(-1)?.close ?? null
      const changeAbsolute = first != null && last != null ? last - first : null
      const changePercent = first != null && first !== 0 && last != null ? (last - first) / first : null
      const status =
        latestSignal?.impact ??
        (changeAbsolute == null ? 'uncertain' : changeAbsolute > 0 ? 'positive' : changeAbsolute < 0 ? 'negative' : 'neutral')

      return {
        assetId: snapshot.assetId,
        symbol,
        name: latestSignal?.asset.name ?? relation?.relation.reason ?? symbol,
        instrumentType: latestSignal?.asset.instrumentType ?? instrumentTypeFromRelationship(relation?.relation.relationship),
        signalCount: matchingSignals.length,
        eventCount: relatedEvents.length,
        latestSignal,
        latestEvent: relatedEvents.toSorted((left, right) => right.eventAt.localeCompare(left.eventAt))[0] ?? null,
        snapshot,
        price: last,
        currency: snapshot.currency,
        changeAbsolute,
        changePercent,
        status,
      }
    })
    .toSorted((left, right) => {
      if (left.signalCount !== right.signalCount) return right.signalCount - left.signalCount
      return left.symbol.localeCompare(right.symbol)
    })
}

export function mapEvidence(evidence: ApiEvidence): EvidenceViewModel {
  return {
    id: evidence.id,
    claim: evidence.claim,
    evidenceType: evidence.evidenceType,
    supportsSignal: evidence.supportsSignal,
    sourceUrl: evidence.sourceUrl,
    linkable: isEvidenceLinkable(evidence),
    excerpt: evidence.excerpt,
    articleId: evidence.articleId,
    sourceId: evidence.sourceId,
    publishedAt: evidence.publishedAt,
    retrievedAt: evidence.retrievedAt,
    raw: evidence,
  }
}

export function mapBriefing(briefing: ApiBriefing, meta?: ApiMeta): BriefingViewModel {
  return {
    id: briefing.briefingId,
    status: briefing.status,
    createdAt: briefing.createdAt,
    updatedAt: briefing.updatedAt,
    executiveSummary: briefing.executiveSummary,
    watchlist: briefing.watchlist,
    prioritizedSignals: briefing.prioritizedSignals,
    humanReviewSummary: briefing.humanReviewSummary,
    reviewTasks: briefing.reviewTasks,
    meta: mapMeta(meta),
    raw: briefing,
  }
}

export function mapRun(run: ApiAgentRun, steps: ApiAgentRunStep[], meta?: ApiMeta): RunViewModel {
  const warnings = Array.from(
    new Set(
      steps.flatMap(step => {
        const candidate = step.payload['warnings']
        return Array.isArray(candidate) ? candidate.filter(item => typeof item === 'string') : []
      }),
    ),
  )

  return {
    id: run.id,
    status: run.status,
    currentNode: run.currentNode,
    modelName: run.modelName,
    promptVersion: run.promptVersion,
    startedAt: run.startedAt,
    finishedAt: run.finishedAt,
    retryCount: run.retryCount,
    warnings,
    meta: mapMeta(meta),
    steps,
    raw: run,
  }
}

export function deriveAssetSummaries(signals: SignalViewModel[], events: EventViewModel[]): AssetSummaryViewModel[] {
  const grouped = new Map<string, AssetSummaryViewModel>()

  for (const signal of signals) {
    const current = grouped.get(signal.asset.symbol) ?? {
      symbol: signal.asset.symbol,
      name: signal.asset.name,
      instrumentType: signal.asset.instrumentType,
      signalCount: 0,
      eventCount: 0,
      averageConfidence: 0,
      latestSignal: null,
      signals: [],
      relatedEvents: [],
    }

    current.signalCount += 1
    current.signals.push(signal)
    current.averageConfidence =
      current.signals.reduce((total, item) => total + item.confidence, 0) / current.signals.length
    current.latestSignal =
      current.latestSignal && current.latestSignal.updatedAt > signal.updatedAt ? current.latestSignal : signal
    grouped.set(signal.asset.symbol, current)
  }

  for (const event of events) {
    for (const asset of event.relatedAssets) {
      const current = grouped.get(asset.symbol)
      if (!current) continue
      if (!current.relatedEvents.some(item => item.id === event.id)) {
        current.relatedEvents.push(event)
      }
      current.eventCount = current.relatedEvents.length
    }
  }

  return Array.from(grouped.values()).toSorted((left, right) => right.signalCount - left.signalCount)
}

export function deriveReviewQueue(
  signals: SignalViewModel[],
  events: EventViewModel[],
  reviewsBySignal: Map<string, ApiSignalReview[]>,
): ReviewQueueItemViewModel[] {
  return signals.map(signal => {
    const latestReview = reviewsBySignal.get(signal.id)?.[0] ?? null
    const event = events.find(item => item.id === signal.eventId) ?? null
    const blockingReason =
      signal.analysisStatus !== 'completed'
        ? 'El análisis aún no está completado.'
        : signal.reviewStatus === 'discarded'
          ? 'La señal ya fue descartada.'
          : null

    return {
      signal,
      event,
      latestReview,
      blockingReason,
    }
  })
}

export function mapWatchlist(watchlist: ApiWatchlist, signals: SignalViewModel[], events: EventViewModel[]): WatchlistViewModel {
  const matchingSignals = signals.filter(signal => {
    const event = events.find(item => item.id === signal.eventId)
    return (
      watchlist.assetIds.includes(signal.asset.symbol) ||
      watchlist.assetIds.includes(signal.eventId) ||
      Boolean(event?.relatedAssets.some(asset => watchlist.assetIds.includes(asset.assetId)))
    )
  })
  const assets = deriveAssetSummaries(signals, events)
  return {
    ...watchlist,
    signals: matchingSignals,
    assets,
  }
}
