import { AlertTriangle, Bot, CheckCircle2, Clock3, Radio, ShieldAlert } from 'lucide-react'
import type { ApiAnalysisStatus, ApiDataMode, ApiImpact, ApiReviewStatus } from '../api/contracts'
import { compactId, formatRelativeTime, toSentenceCase } from '../lib/format'

export function DataModeBadge({ mode }: { mode: ApiDataMode }) {
  return <span className={`badge badge--mode badge--${mode}`}>{mode}</span>
}

export function ImpactBadge({ impact }: { impact: ApiImpact }) {
  return <span className={`badge badge--impact badge--${impact}`}>{toSentenceCase(impact)}</span>
}

export function ReviewStatusBadge({ status }: { status: ApiReviewStatus }) {
  return <span className={`badge badge--review badge--${status}`}>{toSentenceCase(status)}</span>
}

export function AnalysisStatusBadge({ status }: { status: ApiAnalysisStatus }) {
  const icon =
    status === 'completed' ? <CheckCircle2 size={14} /> : status === 'processing' ? <Clock3 size={14} /> : <ShieldAlert size={14} />
  return (
    <span className={`badge badge--analysis badge--${status}`}>
      {icon}
      {toSentenceCase(status)}
    </span>
  )
}

export function DataFreshnessIndicator({ asOf, retrievedAt }: { asOf: string; retrievedAt: string }) {
  return (
    <div className="freshness-indicator" title={`Data as of ${asOf}`}>
      <Radio size={14} />
      <span>Actualizado {formatRelativeTime(retrievedAt)}</span>
    </div>
  )
}

export function AgentStatus({ status, modelName, currentNode }: { status: ApiAnalysisStatus; modelName?: string | null; currentNode?: string }) {
  return (
    <div className="agent-status">
      <Bot size={15} />
      <div>
        <strong>{toSentenceCase(status)}</strong>
        <span>
          {currentNode ? compactId(currentNode) : 'Sin ejecucion activa'}
          {modelName ? ` · ${modelName}` : ''}
        </span>
      </div>
    </div>
  )
}

export function WarningList({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null

  return (
    <div className="warning-list">
      <div className="warning-list__title">
        <AlertTriangle size={15} />
        <span>Advertencias de datos</span>
      </div>
      <ul>
        {warnings.map(warning => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </div>
  )
}
