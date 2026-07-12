import type { AnalysisStatus, StepStatus, AgentRunStatus, ReviewStatus, DataMode, Impact, InstrumentType } from './types';

export const TRANSLATIONS = {
  // Mapeos de enums y contratos (Solo presentación visual al usuario)
  statuses: {
    completed: 'Completado',
    processing: 'Procesando',
    insufficient_evidence: 'Evidencia Insuficiente',
    failed: 'Fallido',
    success: 'Exitoso',
    running: 'Ejecutándose',
    pending: 'Pendiente',
    error: 'Error',
  } as Record<AnalysisStatus | StepStatus | AgentRunStatus, string>,

  reviewStatuses: {
    pending_review: 'Pendiente de Revisión',
    reviewed: 'Aprobado',
    escalated: 'Escalado',
    discarded: 'Descartado',
  } as Record<ReviewStatus, string>,

  dataModes: {
    fixture: 'Datos de Prueba',
    live: 'Datos en Vivo',
    fallback: 'Modo de Contingencia',
  } as Record<DataMode, string>,

  runtime: {
    dataMode: 'Modo de datos',
    warnings: 'Advertencias de datos',
  },

  impacts: {
    positive: 'Positivo',
    negative: 'Negativo',
    neutral: 'Neutral',
    uncertain: 'Incierto',
  } as Record<Impact, string>,

  instrumentTypes: {
    equity: 'Acción',
    etf: 'ETF',
    crypto: 'Criptoactivo',
    commodity: 'Commodity',
    macro: 'Tema Macro',
    credit: 'Credito',
    other: 'Otro',
  } as Record<InstrumentType, string>,

  // Layout y Navegación
  navigation: {
    radar: 'Radar de Eventos',
    briefing: 'Briefing Ejecutivo',
    audit: 'Consola de Auditoría',
  },

  // Vista de Radar
  radar: {
    title: 'Radar de Eventos',
    subtitle: 'Descubrimiento en tiempo real de noticias y eventos que impactan el mercado.',
    searchPlaceholder: 'Buscar activo (ej. NVDA)...',
    allInstruments: 'Todos los Instrumentos',
    anyTime: 'Cualquier momento',
    last24h: 'Últimas 24h',
    last7d: 'Últimos 7 días',
    noEventsTitle: 'No se encontraron eventos',
    noEventsSubtitle: 'Ajusta los filtros para ver más resultados.',
    featuredSignalBadge: 'Señal Destacada',
    featuredAnalysis: 'Análisis de impacto crítico en curso para este activo. Se han detectado movimientos inusuales de volumen correlacionados con este evento.',
    sourcesCount: 'fuentes',
    loading: 'Generando radar de eventos...',
  },

  // Vista de Detalle de Señal
  signalDetail: {
    disclaimerTitle: 'Aviso de Sistema:',
    disclaimerText: 'Esta señal es generada por agentes autónomos de IA y NO constituye asesoramiento financiero ni recomendación de inversión. Tampoco garantiza retornos ni resultados futuros. Requiere revisión humana especializada.',
    estimatedImpact: 'Impacto Estimado:',
    confidence: 'Confianza',
    confidenceLow: 'Bajo',
    confidenceMid: 'Medio',
    confidenceHigh: 'Alto',
    marketSnapshot: 'Contexto de Mercado',
    vsBenchmark: 'Vs Benchmark (Punto de Referencia)',
    underperform: 'Bajo rendimiento',
    outperform: 'Sobre rendimiento',
    dataAsOf: 'Datos actualizados a:',
    retrievedAt: 'Recuperado en:',
    favorableEvidence: 'Evidencia Favorable Corroborada',
    noFavorableEvidence: 'No se encontró evidencia favorable robusta.',
    contrastingEvidence: 'Contraste / Riesgos',
    noContrastingEvidence: 'No se detectó evidencia contradictoria en las fuentes.',
    assumptions: 'Supuestos Críticos',
    invalidations: 'Invalidaciones',
    suggestedActions: 'Acciones Sugeridas',
    loading: 'Cargando contexto de señal...',
    errorLoading: 'Error cargando señal.',
    viewEvidenceSource: 'Ver Evidencia Origen',
    sourceTier: 'Nivel',
    cryptographicHash: 'Hash criptográfico de evidencia',
    
    // Centro de Revisión Humana (Aclarado para analistas humanos)
    humanReviewCenter: 'Centro de Revisión Humana',
    analystDecision: 'Tu validación de analista',
    analystDecisionSubtitle: 'Modifica y valida la propuesta del agente autónomo agregando una justificación obligatoria.',
    reviewStatusLabel: 'Estado de Revisión',
    justificationLabel: 'Justificación / Notas del Analista (Obligatorio)',
    justificationPlaceholder: 'Ingrese detalladamente los motivos de la decisión o comentarios adicionales de revisión...',
    confirmButton: 'Confirmar Decisión',
    approveAction: 'Aprobar',
    escalateAction: 'Escalar',
    discardAction: 'Descartar',
    saveMockSuccess: 'Cambio guardado en backend local',
    sessionHistory: 'Historial de Decisiones (Esta Sesión)',
  },

  // Vista de Briefing
  briefing: {
    draftBadge: 'Borrador de Briefing',
    executiveBadge: 'Briefing Ejecutivo',
    quickStats: 'Estadísticas Rápidas',
    totalSignals: 'TOTAL DE SEÑALES:',
    inconsistencies: 'INCONSISTENCIAS:',
    inconsistencyAlertTitle: 'Inconsistencia Detectada en Estado Compartible',
    inconsistencyAlertText: 'El estado de este briefing está marcado como shareable (compartible), pero contiene señales con estado Descartado o Evidencia Insuficiente. La compartición externa ha sido bloqueada.',
    watchlistSignalsTitle: 'Señales Clave',
    impactLabel: 'Impacto:',
    viewDetailButton: 'Ver Detalle',
    suggestedResearchTitle: 'Acciones de Investigación Sugeridas',
    exportButton: 'Exportar Briefing',
    loading: 'Generando briefing...',
    errorLoading: 'Error al cargar el briefing.',
    positiveSignalsCount: 'Señales Positivas',
    negativeSignalsCount: 'Señales Negativas',
    uncertainSignalsCount: 'Señales Inciertas',
    pendingReviewCount: 'Pendientes de Revisión',
    activeBadge: 'Activo',
    riskBadge: 'Riesgo',
    alertBadge: 'Alerta',
    pendingBadge: 'Pendiente',
    draftTooltip: 'No se puede compartir un borrador',
    inconsistencyTooltip: 'Corrija las inconsistencias para compartir',
    exportTooltip: 'Exportar Briefing',
  },

  // Vista de Auditoría
  audit: {
    consoleHeader: 'Consola de Ejecuciones del Agente',
    runId: 'ID DE EJECUCIÓN:',
    signalId: 'ID DE SEÑAL:',
    mode: 'Modo',
    status: 'Estado',
    duration: 'Duración',
    connectingStream: 'Conectando a stream de auditoría...',
    errorLoading: 'Error cargando auditoría de agente.',
    timelineEnd: 'Fin del registro de auditoría.',
  }
};
