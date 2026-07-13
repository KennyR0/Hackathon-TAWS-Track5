import { createContext, useContext } from 'react'
import type { EventViewModel, SignalViewModel } from '../../shared/types/view-models'

export type GuidedDemoStepId =
  | 'radar'
  | 'signal'
  | 'evidence'
  | 'review'
  | 'briefing'
  | 'briefing-detail'
  | 'analysis'
  | 'audit'

export interface GuidedDemoStep {
  id: GuidedDemoStepId
  title: string
  description: string
  lookAt: string
  target: string
}

export interface GuidedDemoContextValue {
  active: boolean
  currentStep: GuidedDemoStep
  currentIndex: number
  totalSteps: number
  error: string | null
  isBusy: boolean
  canUsePrimaryAction: boolean
  primaryLabel: string
  secondaryLabel: string
  start: () => void
  stop: () => void
  restart: () => void
  next: () => Promise<void>
  skip: () => void
  target: string
  selectedSignal: SignalViewModel | null
  selectedEvent: EventViewModel | null
  briefingId: string | null
  runId: string | null
}

export const GuidedDemoContext = createContext<GuidedDemoContextValue | null>(null)

export function useGuidedDemoTour(): GuidedDemoContextValue {
  const value = useContext(GuidedDemoContext)
  if (!value) throw new Error('useGuidedDemoTour must be used inside GuidedDemoProvider')
  return value
}
