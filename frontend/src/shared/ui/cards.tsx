import { Link } from 'react-router-dom'
import type { BriefingViewModel, EventViewModel, RunViewModel, SignalViewModel } from '../types/view-models'
import { compactId, formatConfidence, formatDateTime, formatPercent, formatRelativeTime, toSentenceCase } from '../lib/format'
import { AnalysisStatusBadge, DataModeBadge, ImpactBadge, ReviewStatusBadge } from './badges'

export function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint ? <small>{hint}</small> : null}
    </article>
  )
}

export function EventCard({ event }: { event: EventViewModel }) {
  return (
    <article className="list-card">
      <div className="list-card__header">
        <div>
          <p className="section-eyebrow">Radar</p>
          <h3>{event.title}</h3>
        </div>
        <DataModeBadge mode={event.meta.dataMode} />
      </div>
      <p>{event.summary}</p>
      <div className="data-points">
        <span>{formatDateTime(event.eventAt)}</span>
        <span>{event.independentSourceCount} fuentes independientes</span>
        <span>{event.relatedAssets.map(asset => asset.symbol).join(', ') || 'Sin activos ligados'}</span>
      </div>
      <div className="card-actions">
        <Link className="text-link" to={`/radar?event=${event.id}`}>
          Ver en radar
        </Link>
      </div>
    </article>
  )
}

export function SignalCard({ signal }: { signal: SignalViewModel }) {
  return (
    <article className="list-card">
      <div className="list-card__header">
        <div>
          <p className="section-eyebrow">{signal.asset.symbol}</p>
          <h3>{signal.asset.name}</h3>
        </div>
        <ImpactBadge impact={signal.impact} />
      </div>
      <p>{signal.thesis ?? 'Sin tesis sintetizada todavia.'}</p>
      <div className="badge-row">
        <AnalysisStatusBadge status={signal.analysisStatus} />
        <ReviewStatusBadge status={signal.reviewStatus} />
        <DataModeBadge mode={signal.meta.dataMode} />
      </div>
      <div className="data-points">
        <span>Confianza {formatConfidence(signal.confidence)}</span>
        <span>Actualizado {formatRelativeTime(signal.updatedAt)}</span>
        <span>{signal.priceReaction ? formatPercent(signal.priceReaction.assetReturn) : 'Sin reaccion cuantificada'}</span>
      </div>
      <div className="card-actions">
        <Link className="text-link" to={`/signals/${signal.id}`}>
          Abrir senal
        </Link>
        <Link className="text-link" to={`/assets/${signal.asset.symbol}`}>
          Ver activo
        </Link>
      </div>
    </article>
  )
}

export function BriefingCard({ briefing }: { briefing: BriefingViewModel }) {
  return (
    <article className="list-card">
      <div className="list-card__header">
        <div>
          <p className="section-eyebrow">{briefing.watchlist.name}</p>
          <h3>{toSentenceCase(briefing.status)}</h3>
        </div>
        <DataModeBadge mode={briefing.meta.dataMode} />
      </div>
      <p>{briefing.executiveSummary}</p>
      <div className="data-points">
        <span>{briefing.prioritizedSignals.length} senales</span>
        <span>{briefing.reviewTasks.filter(task => task.status === 'open').length} tareas abiertas</span>
        <span>{formatDateTime(briefing.updatedAt)}</span>
      </div>
      <div className="card-actions">
        <Link className="text-link" to={`/briefings/${briefing.id}`}>
          Abrir briefing
        </Link>
      </div>
    </article>
  )
}

export function RunCard({ run }: { run: RunViewModel }) {
  return (
    <article className="list-card">
      <div className="list-card__header">
        <div>
          <p className="section-eyebrow">Run {compactId(run.id)}</p>
          <h3>{toSentenceCase(run.currentNode)}</h3>
        </div>
        <AnalysisStatusBadge status={run.status} />
      </div>
      <div className="data-points">
        <span>{run.steps.length} pasos</span>
        <span>{formatDateTime(run.startedAt)}</span>
        <span>{run.modelName ?? 'Modelo no reportado'}</span>
      </div>
      <div className="card-actions">
        <Link className="text-link" to={`/audit/${run.id}`}>
          Ver auditoria
        </Link>
      </div>
    </article>
  )
}
