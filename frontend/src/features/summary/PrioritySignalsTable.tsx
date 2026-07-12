import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { formatConfidence } from '../../shared/lib/format'
import type { SignalViewModel } from '../../shared/types/view-models'
import { ImpactBadge, ReviewStatusBadge } from '../../shared/ui/badges'

export function PrioritySignalsTable({ signals }: { signals: SignalViewModel[] }) {
  return (
    <section className="panel priority-table" aria-labelledby="priority-signals-title">
      <header className="panel-heading">
        <div><p className="section-eyebrow">Señales priorizadas</p><h2 id="priority-signals-title">Decisiones con evidencia</h2></div>
        <Link className="text-link" to="/signals">Ver todas <ArrowRight size={15} /></Link>
      </header>
      <div className="dense-table" role="table" aria-label="Señales priorizadas">
        <div className="dense-table-head signal-grid" role="row">
          <span>Activo</span><span>Impacto</span><span>Conf.</span><span>Revisión</span><span>Tesis</span><span />
        </div>
        {signals.slice(0, 5).map(signal => (
          <Link className="dense-table-row signal-grid" role="row" key={signal.id} to={`/signals/${signal.id}`}>
            <strong className="mono">{signal.asset.symbol}</strong>
            <ImpactBadge impact={signal.impact} />
            <span className="numeric">{formatConfidence(signal.confidence)}</span>
            <ReviewStatusBadge status={signal.reviewStatus} />
            <span className="truncate-copy">{signal.thesis ?? 'Tesis pendiente de síntesis.'}</span>
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        ))}
      </div>
    </section>
  )
}
