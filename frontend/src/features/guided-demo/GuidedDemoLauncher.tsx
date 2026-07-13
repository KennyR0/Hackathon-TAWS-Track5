import { Route } from 'lucide-react'
import { useGuidedDemoTour } from './guidedDemoContext'

export function GuidedDemoLauncher() {
  const tour = useGuidedDemoTour()

  return (
    <button className="guided-demo-launcher" type="button" onClick={tour.active ? tour.restart : tour.start}>
      <Route size={15} />
      <span>{tour.active ? 'Reiniciar recorrido' : 'Iniciar recorrido'}</span>
    </button>
  )
}
