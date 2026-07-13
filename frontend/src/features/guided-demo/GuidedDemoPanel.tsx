import { ArrowRight, RotateCcw, X } from 'lucide-react'
import { GuidedDemoHighlight } from './GuidedDemoHighlight'
import { useGuidedDemoTour } from './guidedDemoStore'

export function GuidedDemoPanel() {
  const tour = useGuidedDemoTour()

  if (!tour.active) return null

  return (
    <>
      <GuidedDemoHighlight target={tour.target} />
      <aside className="guided-demo-panel" aria-label="Recorrido guiado para jurado">
        <header>
          <div>
            <p className="section-eyebrow">Recorrido guiado</p>
            <h2>{tour.currentStep.title}</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Cerrar recorrido" onClick={tour.stop}>
            <X size={16} />
          </button>
        </header>

        <div className="guided-demo-progress" aria-label={`Paso ${tour.currentIndex + 1} de ${tour.totalSteps}`}>
          <span style={{ width: `${((tour.currentIndex + 1) / tour.totalSteps) * 100}%` }} />
        </div>

        <p>{tour.currentStep.description}</p>
        <div className="guided-demo-lookout">
          <strong>Qué mirar</strong>
          <span>{tour.currentStep.lookAt}</span>
        </div>

        {tour.error ? <p className="guided-demo-error" role="alert">{tour.error}</p> : null}

        <div className="guided-demo-actions">
          <button className="primary-button" type="button" onClick={() => void tour.next()} disabled={!tour.canUsePrimaryAction}>
            {tour.primaryLabel}
            <ArrowRight size={15} />
          </button>
          <button className="secondary-button" type="button" onClick={tour.currentIndex >= tour.totalSteps - 1 ? tour.stop : tour.skip}>
            {tour.secondaryLabel}
          </button>
          <button className="text-link guided-demo-reset" type="button" onClick={tour.restart}>
            <RotateCcw size={14} />
            Reiniciar
          </button>
        </div>
      </aside>
    </>
  )
}
