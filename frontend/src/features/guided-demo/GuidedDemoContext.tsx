import { useCallback, useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  useCreateAnalysisMutation,
  useCreateBriefingMutation,
  useCreateReviewMutation,
  useEventsQuery,
  useSignalsQuery,
  useWatchlistQuery,
} from '../../shared/api/queries'
import type { EventViewModel, SignalViewModel } from '../../shared/types/view-models'
import { GuidedDemoContext } from './guidedDemoStore'
import type { GuidedDemoContextValue, GuidedDemoStep, GuidedDemoStepId } from './guidedDemoStore'

const STORAGE_KEY = 'nexomercado:guided-demo-tour'
const REVIEW_JUSTIFICATION = 'Decisión revisada para presentación: la señal cuenta con evidencia verificable y mantiene advertencias visibles.'

interface GuidedDemoState {
  active: boolean
  stepId: GuidedDemoStepId
  signalId: string | null
  eventId: string | null
  briefingId: string | null
  runId: string | null
}

const steps: GuidedDemoStep[] = [
  {
    id: 'radar',
    title: 'Radar verificable',
    description: 'Arrancamos por los eventos: fuentes, activos relacionados y modo de datos visible.',
    lookAt: 'Mira el evento AAPL si está disponible; si no, usamos la primera señal con evidencia.',
    target: 'radar-events',
  },
  {
    id: 'signal',
    title: 'Señal explicable',
    description: 'Entramos a la señal para conectar evento, activo, impacto y estado de revisión.',
    lookAt: 'Observa tesis, confianza, impacto y advertencias; la interfaz no inventa cifras.',
    target: 'signal-thesis',
  },
  {
    id: 'evidence',
    title: 'Evidencia y abstención',
    description: 'El jurado debe ver que cada afirmación tiene respaldo o contraevidencia trazable.',
    lookAt: 'Revisa fuentes, claims, contraevidencia y enlaces originales.',
    target: 'signal-evidence',
  },
  {
    id: 'review',
    title: 'Control humano',
    description: 'La decisión final no la toma el agente: queda justificada por una revisión humana.',
    lookAt: 'Guarda una revisión real con justificación; queda en backend y se refleja en el flujo.',
    target: 'review-console',
  },
  {
    id: 'briefing',
    title: 'Briefing draft',
    description: 'Convertimos señales revisables en una lectura ejecutiva sin prometer rendimiento.',
    lookAt: 'El draft permite mostrar tareas pendientes y restricciones editoriales.',
    target: 'briefing-actions',
  },
  {
    id: 'briefing-detail',
    title: 'Reporte para comité',
    description: 'El briefing muestra prioridades, tareas y límites antes de compartir.',
    lookAt: 'Mira resumen ejecutivo, señales priorizadas y control editorial.',
    target: 'briefing-report',
  },
  {
    id: 'analysis',
    title: 'Análisis auditable',
    description: 'Disparamos el workflow real para que los agentes y nodos de control dejen rastro.',
    lookAt: 'El backend crea un run y después veremos los pasos persistidos.',
    target: 'briefing-report',
  },
  {
    id: 'audit',
    title: 'Auditoría reproducible',
    description: 'Cerramos con el timeline: nodos, payloads resumidos, warnings y estado final.',
    lookAt: 'Este es el punto fuerte: el jurado puede reconstruir qué hizo el sistema.',
    target: 'audit-timeline',
  },
]

const defaultState: GuidedDemoState = {
  active: false,
  stepId: 'radar',
  signalId: null,
  eventId: null,
  briefingId: null,
  runId: null,
}

function readStoredState(): GuidedDemoState {
  if (typeof window === 'undefined') return defaultState
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? '')
    return { ...defaultState, ...parsed }
  } catch {
    return defaultState
  }
}

function getStepIndex(stepId: GuidedDemoStepId): number {
  return Math.max(0, steps.findIndex(step => step.id === stepId))
}

function resolveSignal(signals: SignalViewModel[], preferredId: string | null): SignalViewModel | null {
  return (
    signals.find(signal => signal.id === preferredId) ??
    signals.find(signal => signal.asset.symbol.toUpperCase() === 'AAPL') ??
    signals[0] ??
    null
  )
}

function resolveEvent(events: EventViewModel[], signal: SignalViewModel | null, preferredId: string | null): EventViewModel | null {
  return (
    events.find(event => event.id === preferredId) ??
    events.find(event => event.id === signal?.eventId) ??
    events.find(event => event.relatedAssets.some(asset => asset.symbol.toUpperCase() === 'AAPL')) ??
    events[0] ??
    null
  )
}

export function GuidedDemoProvider({ children }: PropsWithChildren) {
  const navigate = useNavigate()
  const location = useLocation()
  const [state, setState] = useState<GuidedDemoState>(() => readStoredState())
  const [error, setError] = useState<string | null>(null)
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()
  const watchlistQuery = useWatchlistQuery()
  const signals = useMemo(() => signalsQuery.data?.items ?? [], [signalsQuery.data?.items])
  const events = useMemo(() => eventsQuery.data?.items ?? [], [eventsQuery.data?.items])
  const selectedSignal = resolveSignal(signals, state.signalId)
  const selectedEvent = resolveEvent(events, selectedSignal, state.eventId)
  const createReview = useCreateReviewMutation(selectedSignal?.id ?? state.signalId ?? '')
  const createBriefing = useCreateBriefingMutation()
  const createAnalysis = useCreateAnalysisMutation()
  const currentIndex = getStepIndex(state.stepId)
  const currentStep = steps[currentIndex] ?? steps[0]
  const isBusy = createReview.isPending || createBriefing.isPending || createAnalysis.isPending

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const navigateForStep = useCallback(
    (stepId: GuidedDemoStepId, nextState: GuidedDemoState) => {
      const signalId = nextState.signalId ?? selectedSignal?.id
      const briefingId = nextState.briefingId
      const runId = nextState.runId
      if (stepId === 'radar') navigate('/radar')
      else if ((stepId === 'signal' || stepId === 'evidence' || stepId === 'review') && signalId) navigate(`/signals/${signalId}`)
      else if (stepId === 'briefing') navigate('/briefings')
      else if ((stepId === 'briefing-detail' || stepId === 'analysis') && briefingId) navigate(`/briefings/${briefingId}`)
      else if (stepId === 'audit' && runId) navigate(`/audit/${runId}`)
      else if (stepId === 'audit') navigate('/audit')
    },
    [navigate, selectedSignal?.id],
  )

  const setStep = useCallback(
    (stepId: GuidedDemoStepId, patch: Partial<GuidedDemoState> = {}) => {
      setError(null)
      setState(previous => {
        const next = { ...previous, ...patch, active: true, stepId }
        queueMicrotask(() => navigateForStep(stepId, next))
        return next
      })
    },
    [navigateForStep],
  )

  const start = useCallback(() => {
    const signal = resolveSignal(signals, state.signalId)
    const event = resolveEvent(events, signal, state.eventId)
    setStep('radar', {
      signalId: signal?.id ?? null,
      eventId: event?.id ?? signal?.eventId ?? null,
    })
  }, [events, setStep, signals, state.eventId, state.signalId])

  const stop = useCallback(() => {
    setError(null)
    setState(previous => ({ ...previous, active: false }))
  }, [])

  const restart = useCallback(() => {
    const signal = resolveSignal(signals, null)
    const event = resolveEvent(events, signal, null)
    setStep('radar', {
      signalId: signal?.id ?? null,
      eventId: event?.id ?? signal?.eventId ?? null,
      briefingId: null,
      runId: null,
    })
  }, [events, setStep, signals])

  const skip = useCallback(() => {
    const next = steps[Math.min(currentIndex + 1, steps.length - 1)]
    setStep(next.id)
  }, [currentIndex, setStep])

  const next = useCallback(async () => {
    setError(null)
    const signal = selectedSignal
    const event = selectedEvent
    try {
      if (currentStep.id === 'radar') {
        if (!signal) throw new Error('Todavía no hay señal disponible para abrir.')
        setStep('signal', { signalId: signal.id, eventId: event?.id ?? signal.eventId })
        return
      }
      if (currentStep.id === 'signal') {
        setStep('evidence')
        return
      }
      if (currentStep.id === 'evidence') {
        setStep('review')
        return
      }
      if (currentStep.id === 'review') {
        if (!signal) throw new Error('No se pudo resolver la señal para revisión.')
        if (signal.reviewStatus !== 'reviewed') {
          await createReview.mutateAsync({
            status: 'reviewed',
            justification: REVIEW_JUSTIFICATION,
          })
        }
        setStep('briefing')
        return
      }
      if (currentStep.id === 'briefing') {
        if (state.briefingId) {
          setStep('briefing-detail', { briefingId: state.briefingId })
          return
        }
        if (!signals.length) throw new Error('No hay señales disponibles para crear el briefing.')
        const response = await createBriefing.mutateAsync({
          signalIds: signals.map(item => item.id),
          status: 'draft',
          watchlistId: watchlistQuery.data?.id ?? 'watchlist_demo_global',
        })
        setStep('briefing-detail', { briefingId: response.data.briefingId })
        return
      }
      if (currentStep.id === 'briefing-detail') {
        setStep('analysis')
        return
      }
      if (currentStep.id === 'analysis') {
        if (state.runId) {
          setStep('audit', { runId: state.runId })
          return
        }
        if (!event) throw new Error('No se pudo resolver el evento para iniciar análisis.')
        const assetIds = event.relatedAssets.map(asset => asset.assetId)
        if (!assetIds.length) throw new Error('El evento no tiene activos relacionados para analizar.')
        const response = await createAnalysis.mutateAsync({ eventId: event.id, assetIds })
        setStep('audit', { runId: response.data.id })
        return
      }
      if (currentStep.id === 'audit') {
        stop()
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo completar este paso.')
    }
  }, [
    createAnalysis,
    createBriefing,
    createReview,
    currentStep.id,
    selectedEvent,
    selectedSignal,
    setStep,
    signals,
    state.briefingId,
    state.runId,
    stop,
    watchlistQuery.data?.id,
  ])

  const primaryLabel = useMemo(() => {
    if (isBusy) return 'Procesando'
    if (currentStep.id === 'radar') return 'Abrir señal'
    if (currentStep.id === 'signal') return 'Ver evidencia'
    if (currentStep.id === 'evidence') return 'Ir a revisión'
    if (currentStep.id === 'review') return selectedSignal?.reviewStatus === 'reviewed' ? 'Continuar a briefing' : 'Guardar revisión y seguir'
    if (currentStep.id === 'briefing') return 'Crear briefing draft'
    if (currentStep.id === 'briefing-detail') return 'Lanzar análisis auditable'
    if (currentStep.id === 'analysis') return 'Ver auditoría'
    return 'Finalizar recorrido'
  }, [currentStep.id, isBusy, selectedSignal?.reviewStatus])

  const canUsePrimaryAction = Boolean(
    selectedSignal ||
    currentStep.id === 'briefing' ||
    currentStep.id === 'briefing-detail' ||
    currentStep.id === 'analysis' ||
    currentStep.id === 'audit',
  ) && !isBusy
  const value = useMemo<GuidedDemoContextValue>(
    () => ({
      active: state.active,
      currentStep,
      currentIndex,
      totalSteps: steps.length,
      error,
      isBusy,
      canUsePrimaryAction,
      primaryLabel,
      secondaryLabel: currentIndex >= steps.length - 1 ? 'Cerrar' : 'Saltar paso',
      start,
      stop,
      restart,
      next,
      skip,
      target: currentStep.target,
      selectedSignal,
      selectedEvent,
      briefingId: state.briefingId,
      runId: state.runId,
    }),
    [
      canUsePrimaryAction,
      currentIndex,
      currentStep,
      error,
      isBusy,
      next,
      primaryLabel,
      restart,
      selectedEvent,
      selectedSignal,
      skip,
      start,
      state.active,
      state.briefingId,
      state.runId,
      stop,
    ],
  )

  useEffect(() => {
    if (!state.active) return
    if (currentStep.id === 'briefing-detail' && state.briefingId && !location.pathname.includes(state.briefingId)) {
      navigate(`/briefings/${state.briefingId}`)
    }
    if (currentStep.id === 'audit' && state.runId && !location.pathname.includes(state.runId)) {
      navigate(`/audit/${state.runId}`)
    }
  }, [currentStep.id, location.pathname, navigate, state.active, state.briefingId, state.runId])

  return <GuidedDemoContext.Provider value={value}>{children}</GuidedDemoContext.Provider>
}
