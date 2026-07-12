import type {
  AgentRun,
  AgentRunStep,
  AnalysisStatus,
  Briefing,
  BriefingStatus,
  DataMode,
  Event,
  Impact,
  InstrumentType,
  ReviewDecisionResult,
  ReviewStatus,
  Signal,
  SourceTier,
  StepStatus,
} from './types';

function normalizeApiBaseUrl(rawValue?: string): string {
  const value = (rawValue?.trim() || '/api').replace(/\/$/, '');
  if (!value) {
    return '/api';
  }
  if (value.endsWith('/api')) {
    return value;
  }
  if (value.startsWith('http://') || value.startsWith('https://')) {
    return `${value}/api`;
  }
  return value;
}

const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL,
);
const API_V1_URL = `${API_BASE_URL}/v1`;
const DEFAULT_SIGNAL_ID = 'sig_btc_uncertain';
const DEFAULT_EVENT_ID = 'evt_aapl_outlook_20260709';
const DEFAULT_ASSET_ID = 'ast_aapl';
const DEFAULT_WATCHLIST_ID = 'watchlist_demo_global';

interface ApiEnvelope<T> {
  data: T;
  meta?: ApiMeta;
}

interface ApiMeta {
  dataMode: DataMode;
  provider: string;
  retrievedAt: string;
  dataAsOf: string;
  warnings: string[];
}

interface ApiSource {
  id: string;
  name: string;
  domain: string;
  tier: SourceTier;
}

interface ApiArticle {
  id: string;
  sourceId: string;
  headline: string;
  summary: string;
  publishedAt: string;
  url: string;
}

interface ApiAssetRelation {
  assetId: string;
  symbol: string;
  relationship: string;
  reason: string;
}

interface ApiEvent {
  id: string;
  title: string;
  summary: string;
  eventAt: string;
  articleIds: string[];
  relatedAssets: ApiAssetRelation[];
}

interface ApiEventView {
  event: ApiEvent;
  articles: ApiArticle[];
  sources: ApiSource[];
}

interface ApiAssetRef {
  symbol: string;
  name: string;
  instrumentType: InstrumentType;
}

interface ApiPriceReaction {
  assetReturn: number;
  benchmarkReturn: number | null;
  abnormalReturn: number | null;
  relativeVolume: number | null;
}

interface ApiReviewSummary {
  status: ReviewStatus;
  justification: string | null;
  reviewedBy: { id: string; name: string } | null;
  reviewedAt: string | null;
}

interface ApiSignal {
  id: string;
  eventId: string;
  asset: ApiAssetRef;
  impact: Impact;
  confidence: number;
  analysisStatus: AnalysisStatus;
  thesis: string | null;
  priceReaction: ApiPriceReaction | null;
  evidenceIds: string[];
  counterEvidenceIds: string[];
  assumptions: string[];
  invalidationConditions: string[];
  suggestedResearchActions: string[];
  review: ApiReviewSummary;
  createdAt: string;
  updatedAt: string;
}

interface ApiEvidence {
  id: string;
  signalId: string;
  claimId: string;
  evidenceType: string;
  supportsSignal: boolean;
  articleId: string | null;
  sourceId: string | null;
  claim: string;
  excerpt: string | null;
  sourceUrl: string;
  publishedAt: string | null;
  retrievedAt: string;
  dataAsOf: string;
  contentHash: string;
}

interface ApiSignalReview {
  id: string;
  signalId: string;
  previousStatus: Exclude<ReviewStatus, 'pending_review'> | 'pending_review';
  status: Exclude<ReviewStatus, 'pending_review'>;
  justification: string;
  reviewedBy: { id: string; name: string };
  reviewedAt: string;
}

interface ApiBriefing {
  briefingId: string;
  status: BriefingStatus;
  watchlist: { id: string; name: string };
  executiveSummary: string;
  prioritizedSignals: {
    signalId: string;
    priority: 'high' | 'medium' | 'low';
    reason: string;
    suggestedResearchActions: string[];
    review: ApiReviewSummary;
  }[];
  humanReviewSummary: {
    totalSignals: number;
    pendingReview: number;
    reviewed: number;
    escalated: number;
    discarded: number;
  };
  createdAt: string;
}

interface ApiAgentRun {
  id: string;
  currentNode: string;
  status: AnalysisStatus;
  modelName: string | null;
  promptVersion: string | null;
  inputHash: string;
  sourceSnapshotIds: string[];
  startedAt: string;
  finishedAt: string | null;
  errorCode: string | null;
  retryCount: number;
}

interface ApiAgentRunStep {
  id: string;
  runId: string;
  node: string;
  status: 'processing' | 'completed' | 'failed' | 'skipped';
  timestamp: string;
  payload: Record<string, unknown>;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_V1_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    let code: string | undefined;
    try {
      const body = await response.json();
      message = body.message ?? message;
      code = body.code;
    } catch {
      // Keep the HTTP fallback message.
    }
    throw new ApiClientError(message, response.status, code);
  }

  return response.json() as Promise<T>;
}

export async function getEvents(filters?: {
  instrumentType?: InstrumentType | 'all';
  asset?: string;
  publishedAfter?: string;
}): Promise<Event[]> {
  const params = new URLSearchParams();
  if (filters?.instrumentType && filters.instrumentType !== 'all') {
    params.set('instrumentType', filters.instrumentType);
  }
  if (filters?.asset) {
    params.set('asset', filters.asset);
  }
  if (filters?.publishedAfter) {
    params.set('publishedAfter', filters.publishedAfter);
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  const payload = await request<ApiEnvelope<ApiEventView[]>>(`/events${query}`);
  return payload.data.map(mapEventView);
}

export async function getSignal(signalId = DEFAULT_SIGNAL_ID): Promise<Signal> {
  const signalPayload = await request<ApiEnvelope<ApiSignal>>(`/signals/${signalId}`);
  const evidencePayload = await request<ApiEnvelope<ApiEvidence[]>>(`/signals/${signalId}/evidence`);
  return mapSignal(signalPayload.data, evidencePayload.data, signalPayload.meta);
}

export async function saveSignalReview(
  signalId: string,
  status: Exclude<ReviewStatus, 'pending_review'>,
  justification: string,
): Promise<ReviewDecisionResult> {
  const idempotencyKey = `review-${signalId}-${status}-${Date.now()}`;
  const reviewsPayload = await request<ApiEnvelope<ApiSignalReview[]>>(`/signals/${signalId}/reviews`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify({ status, justification }),
  });
  const signal = await getSignal(signalId);
  return {
    signal,
    reviews: reviewsPayload.data.map(review => ({
      id: review.id,
      signalId: review.signalId,
      previousStatus: review.previousStatus,
      status: review.status,
      justification: review.justification,
      reviewedBy: review.reviewedBy.name,
      reviewedAt: review.reviewedAt,
    })),
  };
}

export async function createDraftBriefing(): Promise<Briefing> {
  const signalsPayload = await request<ApiEnvelope<ApiSignal[]>>('/signals');
  const signalIds = signalsPayload.data.map(signal => signal.id);
  const briefingPayload = await request<ApiEnvelope<ApiBriefing>>('/briefings', {
    method: 'POST',
    headers: { 'Idempotency-Key': `briefing-demo-${Date.now()}` },
    body: JSON.stringify({
      watchlistId: DEFAULT_WATCHLIST_ID,
      signalIds,
      status: 'draft',
    }),
  });

  const hydratedSignals = await Promise.all(signalIds.map(signalId => getSignal(signalId)));
  return mapBriefing(briefingPayload.data, hydratedSignals, briefingPayload.meta ?? signalsPayload.meta);
}

export async function createAgentRun(): Promise<AgentRun> {
  const runPayload = await request<ApiEnvelope<ApiAgentRun>>('/analyses', {
    method: 'POST',
    headers: { 'Idempotency-Key': `analysis-demo-${Date.now()}` },
    body: JSON.stringify({
      eventId: DEFAULT_EVENT_ID,
      assetIds: [DEFAULT_ASSET_ID],
    }),
  });

  const run = await waitForTerminalRun(runPayload.data.id);
  const stepsPayload = await request<ApiEnvelope<ApiAgentRunStep[]>>(`/runs/${run.id}/steps`);
  return mapAgentRun(run, stepsPayload.data, runPayload.meta ?? stepsPayload.meta);
}

async function waitForTerminalRun(runId: string): Promise<ApiAgentRun> {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const payload = await request<ApiEnvelope<ApiAgentRun>>(`/analyses/${runId}`);
    if (payload.data.status !== 'processing') {
      return payload.data;
    }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new ApiClientError(`La ejecucion ${runId} no termino a tiempo.`, 408, 'timeout');
}

function mapEventView(view: ApiEventView): Event {
  const article = view.articles[0];
  const source = view.sources.find(item => item.id === article?.sourceId) ?? view.sources[0];
  return {
    id: view.event.id,
    headline: view.event.title,
    eventAt: view.event.eventAt,
    assets: view.event.relatedAssets.map(relation => ({
      id: relation.assetId,
      symbol: relation.symbol,
      name: relation.reason,
      instrumentType: mapInstrumentType(relation.relationship),
    })),
    mainArticle: {
      id: article.id,
      title: article.headline,
      url: article.url,
      source: {
        id: source.id,
        name: source.name,
        tier: source.tier,
      },
      publishedAt: article.publishedAt,
    },
    corroboratingCount: Math.max(0, view.sources.filter(item => item.id !== source.id).length),
  };
}

function mapSignal(apiSignal: ApiSignal, evidence: ApiEvidence[], meta?: ApiMeta): Signal {
  const assetReturn = apiSignal.priceReaction?.assetReturn ?? 0;
  const latestEvidence = evidence[0];
  return {
    id: apiSignal.id,
    eventId: apiSignal.eventId,
    asset: {
      id: apiSignal.asset.symbol,
      symbol: apiSignal.asset.symbol,
      name: apiSignal.asset.name,
      instrumentType: apiSignal.asset.instrumentType,
    },
    status: apiSignal.analysisStatus,
    impact: apiSignal.impact,
    reviewStatus: apiSignal.review.status,
    confidenceScore: apiSignal.confidence,
    marketSnapshot: {
      id: latestEvidence?.id ?? `${apiSignal.id}-snapshot`,
      assetId: apiSignal.asset.symbol,
      price: Math.abs(assetReturn * 100),
      currency: 'USD',
      change24h: assetReturn * 100,
      benchmarkSymbol: apiSignal.priceReaction?.benchmarkReturn === null ? undefined : 'SPY',
      benchmarkChange24h:
        apiSignal.priceReaction?.benchmarkReturn === null || apiSignal.priceReaction?.benchmarkReturn === undefined
          ? undefined
          : apiSignal.priceReaction.benchmarkReturn * 100,
      dataAsOf: meta?.dataAsOf ?? latestEvidence?.dataAsOf ?? apiSignal.updatedAt,
      retrievedAt: meta?.retrievedAt ?? latestEvidence?.retrievedAt ?? apiSignal.updatedAt,
    },
    evidences: evidence.map(item => ({
      id: item.id,
      text: item.excerpt ?? item.claim,
      articleId: item.articleId ?? undefined,
      articleTitle: item.claim,
      sourceName: item.sourceId ?? new URL(item.sourceUrl).hostname,
      sourceTier: undefined,
      snapshotId: item.sourceId ?? undefined,
      hash: item.contentHash,
    })),
    favorableEvidenceIds: apiSignal.evidenceIds,
    counterEvidenceIds: apiSignal.counterEvidenceIds,
    claims: [
      ...(apiSignal.thesis
        ? [{ id: `${apiSignal.id}-thesis`, description: apiSignal.thesis, evidenceId: apiSignal.evidenceIds[0] ?? evidence[0]?.id ?? apiSignal.id }]
        : []),
      ...evidence.map(item => ({
        id: item.claimId,
        description: item.claim,
        evidenceId: item.id,
      })),
    ],
    assumptions: apiSignal.assumptions,
    invalidations: apiSignal.invalidationConditions,
    suggestedResearchActions: apiSignal.suggestedResearchActions,
    dataMode: meta?.dataMode ?? 'fixture',
    warnings: meta?.warnings ?? [],
  };
}

function mapBriefing(apiBriefing: ApiBriefing, signals: Signal[], meta?: ApiMeta): Briefing {
  const signalWarnings = signals.flatMap(signal => signal.warnings);
  const warnings = Array.from(new Set([...(meta?.warnings ?? []), ...signalWarnings]));
  const signalById = new Map(signals.map(signal => [signal.id, signal]));
  return {
    id: apiBriefing.briefingId,
    title: `Briefing ${apiBriefing.watchlist.name}`,
    generatedAt: apiBriefing.createdAt,
    status: apiBriefing.status,
    summary: apiBriefing.executiveSummary,
    signals: apiBriefing.prioritizedSignals
      .map(item => signalById.get(item.signalId))
      .filter((signal): signal is Signal => Boolean(signal)),
    dataMode: meta?.dataMode ?? signals[0]?.dataMode ?? 'fixture',
    warnings,
  };
}

function mapAgentRun(run: ApiAgentRun, steps: ApiAgentRunStep[], meta?: ApiMeta): AgentRun {
  return {
    id: run.id,
    signalId: run.currentNode,
    dataMode: meta?.dataMode ?? 'fixture',
    status: mapRunStatus(run.status),
    startedAt: run.startedAt,
    completedAt: run.finishedAt ?? undefined,
    steps: steps.map(mapAgentRunStep),
    warnings: meta?.warnings ?? [],
  };
}

function mapAgentRunStep(step: ApiAgentRunStep): AgentRunStep {
  return {
    id: step.id,
    nodeName: step.node,
    status: mapStepStatus(step.status),
    startedAt: step.timestamp,
    completedAt: step.status === 'completed' || step.status === 'failed' || step.status === 'skipped' ? step.timestamp : undefined,
    ...step.payload,
  };
}

function mapInstrumentType(value: string): InstrumentType {
  if (value === 'direct' || value === 'sector' || value === 'competitor' || value === 'supply_chain') {
    return 'equity';
  }
  if (value === 'commodity') {
    return 'commodity';
  }
  if (value === 'macro') {
    return 'macro';
  }
  if (value === 'credit') {
    return 'credit';
  }
  return 'other';
}

function mapRunStatus(status: AnalysisStatus): AgentRun['status'] {
  if (status === 'processing') {
    return 'running';
  }
  if (status === 'failed') {
    return 'failed';
  }
  return 'completed';
}

function mapStepStatus(status: ApiAgentRunStep['status']): StepStatus {
  if (status === 'processing') {
    return 'running';
  }
  if (status === 'failed') {
    return 'error';
  }
  if (status === 'skipped') {
    return 'pending';
  }
  return 'success';
}

export const demoIds = {
  signalId: DEFAULT_SIGNAL_ID,
  eventId: DEFAULT_EVENT_ID,
  assetId: DEFAULT_ASSET_ID,
};
