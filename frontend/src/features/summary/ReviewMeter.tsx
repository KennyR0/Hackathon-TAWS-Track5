import { Link } from 'react-router-dom'

export function ReviewMeter({ total, reviewed }: { total: number; reviewed: number }) {
  const pending = Math.max(total - reviewed, 0)
  const percentage = total ? Math.round((reviewed / total) * 100) : 0

  return (
    <section className="panel review-meter" aria-labelledby="review-meter-title">
      <header className="panel-heading"><div><p className="section-eyebrow">Control humano</p><h2 id="review-meter-title">Estado de revisión</h2></div></header>
      <strong className="hero-number numeric">{reviewed}<small>/{total}</small></strong>
      <p>señales verificadas</p>
      <div className="meter" aria-label={`${percentage}% de señales revisadas`}><span style={{ width: `${percentage}%` }} /></div>
      <Link className="secondary-button" to="/reviews">{pending ? `Revisar ${pending} pendientes` : 'Ver historial'}</Link>
    </section>
  )
}
