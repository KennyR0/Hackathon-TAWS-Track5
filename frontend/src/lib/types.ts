export type InstrumentType = 'equity' | 'etf' | 'crypto' | 'commodity' | 'macro' | 'credit' | 'other';
export type SourceTier = 'A' | 'B' | 'C' | 'D';

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  instrumentType: InstrumentType;
}

export interface Source {
  id: string;
  name: string;
  tier: SourceTier;
}

export interface Article {
  id: string;
  title: string;
  url: string;
  source: Source;
  publishedAt: string;
}

export interface Event {
  id: string;
  headline: string;
  eventAt: string;
  assets: Asset[];
  mainArticle: Article;
  corroboratingCount: number;
}

export type AnalysisStatus = 'processing' | 'completed' | 'insufficient_evidence' | 'failed';
export type Impact = 'positive' | 'negative' | 'neutral' | 'uncertain';
export type ReviewStatus = 'pending_review' | 'reviewed' | 'escalated' | 'discarded';

export interface MarketSnapshot {
  id: string;
  assetId: string;
  price: number;
  currency: string;
  change24h: number;
  benchmarkSymbol?: string;
  benchmarkChange24h?: number;
  dataAsOf: string;
  retrievedAt: string;
}

export interface Evidence {
  id: string;
  text: string;
  articleId?: string; 
  articleTitle?: string;
  sourceName?: string;
  sourceTier?: SourceTier;
  snapshotId?: string;
  hash: string;
}

export interface Claim {
  id: string;
  description: string;
  evidenceId: string;
}

export interface Signal {
  id: string;
  eventId: string;
  asset: Asset;
  status: AnalysisStatus;
  impact: Impact;
  reviewStatus: ReviewStatus;
  confidenceScore: number; // 0.0 to 1.0
  marketSnapshot: MarketSnapshot;
  claims: Claim[];
  favorableEvidenceIds: string[];
  counterEvidenceIds: string[];
  evidences: Evidence[];
  assumptions: string[];
  invalidations: string[];
  suggestedResearchActions: string[];
}

export interface ReviewDecisionResult {
  signal: Signal;
  reviews: {
    id: string;
    signalId: string;
    previousStatus: ReviewStatus;
    status: Exclude<ReviewStatus, 'pending_review'>;
    justification: string;
    reviewedBy: string;
    reviewedAt: string;
  }[];
}

export type BriefingStatus = 'draft' | 'shareable';

export interface Briefing {
  id: string;
  title: string;
  generatedAt: string;
  status: BriefingStatus;
  summary: string;
  signals: Signal[];
}

// NUEVOS TIPOS: Auditoría (AgentRun)
export type DataMode = 'fixture' | 'live' | 'fallback';
export type AgentRunStatus = 'running' | 'completed' | 'failed';
export type StepStatus = 'pending' | 'running' | 'success' | 'error';

export interface AgentRunStep {
  id: string;
  nodeName: string;
  status: StepStatus;
  startedAt?: string;
  completedAt?: string;
  // Soporte forward-compatible para campos arbitrarios que lleguen de backend después
  [key: string]: any; 
}

export interface AgentRun {
  id: string;
  signalId: string;
  dataMode: DataMode;
  status: AgentRunStatus;
  startedAt: string;
  completedAt?: string;
  steps: AgentRunStep[];
}
