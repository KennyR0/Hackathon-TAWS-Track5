export const fixtureMeta = {
  fixtureId: 'fixture_phase0_v1',
  schemaVersion: '1.0.0',
  clock: '2026-07-11T13:00:00Z',
  mode: 'fixture',
  providerLabel: 'Datos sintéticos · no tiempo real',
}

export const sources = [
  { id: 'src_fixture_finwire', name: 'Nexo Fixture Financial Wire', tier: 'B', country: 'US' },
  { id: 'src_fixture_businessdaily', name: 'Nexo Fixture Business Daily', tier: 'C', country: 'GB' },
]

export const assets = [
  {
    id: 'ast_aapl', symbol: 'AAPL', name: 'Apple Inc.', type: 'Acción', currency: 'USD', exchange: 'NASDAQ',
    provider: 'Twelve Data', retrievedAt: '2026-07-10T20:15:00Z', values: [200, 200.5, 201, 201.5, 202, 202.5, 203, 203.5, 204, 204.5, 205, 205.5, 206, 206.5, 207, 207.5, 208, 208.5, 209, 210, 201.6],
  },
  {
    id: 'ast_spy', symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', type: 'ETF', currency: 'USD', exchange: 'NYSE Arca',
    provider: 'Twelve Data', retrievedAt: '2026-07-10T20:15:00Z', values: [620, 616.28],
  },
  {
    id: 'ast_btc_usd', symbol: 'BTC-USD', name: 'Bitcoin', type: 'Cripto', currency: 'USD', exchange: 'Global',
    provider: 'CoinGecko', retrievedAt: '2026-07-11T12:05:00Z', values: [98000, 98200, 98400, 98600, 98800, 99000, 99200, 99400, 99600, 99800, 100000, 100200, 100400, 100600, 100800, 101000, 101200, 101400, 101600, 101800, 102000, 102200, 102400, 102600, 102800, 103000, 103200, 103400, 103600, 105000, 107100],
  },
  {
    id: 'ast_wti', symbol: 'WTI', name: 'West Texas Intermediate Crude Oil', type: 'Materia prima', currency: 'USD', exchange: '—',
    provider: 'FRED', retrievedAt: '2026-07-11T01:00:00Z', values: [68, 68.2164, 68.4327, 68.6491, 68.8655, 69.0818, 69.2982, 69.5145, 69.7309, 69.9473, 70.1636, 70.38, 70.5964, 70.8127, 71.0291, 71.2455, 71.4618, 71.6782, 71.8945, 72.1109, 72.3273, 72.5436, 72.76],
  },
]

export const events = [
  {
    id: 'evt_aapl_outlook_20260709', symbol: 'AAPL', time: '2026-07-09T20:05:00Z',
    title: 'Ajuste de previsión trimestral de Apple',
    summary: 'Dos publishers sintéticos independientes corroboran el evento.',
    articleIds: ['art_aapl_finwire_20260709', 'art_aapl_businessdaily_20260709'], signalId: 'sig_aapl_negative',
  },
  {
    id: 'evt_btc_policy_20260710', symbol: 'BTC-USD', time: '2026-07-10T12:00:00Z',
    title: 'Cobertura contradictoria de una medida regulatoria sobre Bitcoin',
    summary: 'Dos publishers discrepan sobre si la medida sintética es definitiva.',
    articleIds: ['art_btc_finwire_20260710', 'art_btc_businessdaily_20260710'], signalId: 'sig_btc_uncertain',
  },
  {
    id: 'evt_wti_supply_20260710', symbol: 'WTI', time: '2026-07-10T14:30:00Z',
    title: 'Extensión temporal de recortes de oferta de crudo',
    summary: 'Dos publishers corroboran el evento; el precio se conserva como contexto.',
    articleIds: ['art_wti_finwire_20260710', 'art_wti_businessdaily_20260710'], signalId: 'sig_wti_context',
  },
]

export const articles = [
  { id: 'art_aapl_finwire_20260709', sourceId: 'src_fixture_finwire', publishedAt: '2026-07-09T20:15:00Z', headline: 'Apple reduce su previsión trimestral en el escenario de demostración', summary: 'El publisher informa una reducción de la previsión tras el cierre del mercado.' },
  { id: 'art_aapl_businessdaily_20260709', sourceId: 'src_fixture_businessdaily', publishedAt: '2026-07-09T20:25:00Z', headline: 'Segundo publisher confirma el ajuste de previsión de Apple', summary: 'Una cobertura independiente confirma el mismo ajuste trimestral sintético.' },
  { id: 'art_btc_finwire_20260710', sourceId: 'src_fixture_finwire', publishedAt: '2026-07-10T12:10:00Z', headline: 'Un reporte describe como definitiva una medida regulatoria sobre Bitcoin', summary: 'El primer publisher presenta la medida sintética como una aprobación final.' },
  { id: 'art_btc_businessdaily_20260710', sourceId: 'src_fixture_businessdaily', publishedAt: '2026-07-10T12:25:00Z', headline: 'Otra cobertura señala que la medida sobre Bitcoin sigue en consulta', summary: 'El segundo publisher contradice materialmente el carácter definitivo del anuncio.' },
  { id: 'art_wti_finwire_20260710', sourceId: 'src_fixture_finwire', publishedAt: '2026-07-10T14:40:00Z', headline: 'Productores extienden recortes temporales de oferta de crudo', summary: 'El publisher reporta una extensión sintética de recortes de oferta.' },
  { id: 'art_wti_businessdaily_20260710', sourceId: 'src_fixture_businessdaily', publishedAt: '2026-07-10T14:55:00Z', headline: 'Fuente independiente confirma la extensión de recortes de crudo', summary: 'La segunda cobertura corrobora el evento, sin afirmar causalidad de precio.' },
]

export const signals = [
  {
    id: 'sig_aapl_negative', eventId: 'evt_aapl_outlook_20260709', symbol: 'AAPL', assetName: 'Apple Inc.', impact: 'negative', confidence: 0.81, reviewStatus: 'reviewed',
    thesis: 'El ajuste corroborado coincide con una reacción negativa de AAPL superior a la de SPY; la relación no demuestra causalidad por sí sola.',
    metrics: { assetReturn: -0.04, benchmarkReturn: -0.006, abnormalReturn: -0.034, relativeVolume: 2 },
    assumptions: ['El primer cierre posterior es una ventana válida para el evento.'],
    invalidation: ['El ajuste se revierte o se demuestra que el movimiento precedió al evento.'],
    nextAction: 'Contrastar el ajuste con el documento corporativo oficial.',
    disclaimer: 'Esta señal es informativa, no constituye asesoría financiera personalizada ni garantiza resultados.',
  },
  {
    id: 'sig_btc_uncertain', eventId: 'evt_btc_policy_20260710', symbol: 'BTC-USD', assetName: 'Bitcoin', impact: 'uncertain', confidence: 0.40, reviewStatus: 'pending_review',
    thesis: 'La reacción de 24 horas es observable, pero la contradicción material impide clasificar el impacto del anuncio.',
    metrics: { assetReturn: 0.02, benchmarkReturn: null, abnormalReturn: null, relativeVolume: null },
    assumptions: [], invalidation: ['Una fuente primaria confirma el estado regulatorio definitivo.'],
    nextAction: 'Localizar la resolución regulatoria primaria antes de reclasificar.',
    disclaimer: 'Esta señal es informativa, no constituye asesoría financiera personalizada ni garantiza resultados.',
  },
  {
    id: 'sig_wti_context', eventId: 'evt_wti_supply_20260710', symbol: 'WTI', assetName: 'West Texas Intermediate Crude Oil', impact: 'positive', confidence: 0.72, reviewStatus: 'pending_review',
    thesis: 'La extensión corroborada coincide con un avance de 7 % del WTI en 30 días, usado únicamente como contexto y no como prueba causal.',
    metrics: { assetReturn: 0.07, benchmarkReturn: null, abnormalReturn: null, relativeVolume: null },
    assumptions: [], invalidation: ['Los recortes no se materializan durante la ventana anunciada.'],
    nextAction: 'Comparar el evento con inventarios y demanda antes de atribuir causalidad.',
    disclaimer: 'Esta señal es informativa, no constituye asesoría financiera personalizada ni garantiza resultados.',
  },
]

export const evidence = [
  { id: 'evd_aapl_finwire', signalId: 'sig_aapl_negative', type: 'Fuente', supports: true, sourceId: 'src_fixture_finwire', text: 'El escenario reduce la previsión trimestral después del cierre.' },
  { id: 'evd_aapl_businessdaily', signalId: 'sig_aapl_negative', type: 'Fuente', supports: true, sourceId: 'src_fixture_businessdaily', text: 'La cobertura independiente confirma el mismo ajuste sintético.' },
  { id: 'evd_aapl_asset_return', signalId: 'sig_aapl_negative', type: 'Cálculo', supports: true, text: 'AAPL cayó 4 % entre el cierre anterior y el primer cierre posterior.' },
  { id: 'evd_aapl_benchmark_return', signalId: 'sig_aapl_negative', type: 'Cálculo', supports: true, text: 'SPY cayó 0,6 % en la misma ventana de cierres.' },
  { id: 'evd_aapl_abnormal_return', signalId: 'sig_aapl_negative', type: 'Cálculo', supports: true, text: 'El retorno anormal simplificado de AAPL frente a SPY fue -3,4 %.' },
  { id: 'evd_aapl_relative_volume', signalId: 'sig_aapl_negative', type: 'Cálculo', supports: true, text: 'El volumen de AAPL fue 2 veces la media de las 20 sesiones previas.' },
  { id: 'evd_btc_finwire_support', signalId: 'sig_btc_uncertain', type: 'Fuente', supports: true, sourceId: 'src_fixture_finwire', text: 'El primer publisher describe la medida como una aprobación final.' },
  { id: 'evd_btc_businessdaily_counter', signalId: 'sig_btc_uncertain', type: 'Contraevidencia', supports: false, sourceId: 'src_fixture_businessdaily', text: 'El segundo publisher afirma que la medida sigue en consulta.' },
  { id: 'evd_btc_market', signalId: 'sig_btc_uncertain', type: 'Dato de mercado', supports: true, text: 'BTC-USD subió 2 % durante las 24 horas posteriores al evento.' },
  { id: 'evd_wti_finwire', signalId: 'sig_wti_context', type: 'Fuente', supports: true, sourceId: 'src_fixture_finwire', text: 'La cobertura reporta una extensión temporal de recortes de oferta.' },
  { id: 'evd_wti_businessdaily', signalId: 'sig_wti_context', type: 'Fuente', supports: true, sourceId: 'src_fixture_businessdaily', text: 'La fuente independiente corrobora el evento sin atribuir causalidad.' },
  { id: 'evd_wti_market', signalId: 'sig_wti_context', type: 'Contexto', supports: true, text: 'WTI subió 7 % en la ventana de 30 días usada como contexto.' },
]

export const briefing = {
  id: 'brf_demo_global_20260711', status: 'draft', name: 'Demo Global', updatedAt: '2026-07-11T12:45:00Z',
  summary: 'El corpus contiene una señal revisada, una abstención por contradicción y una señal contextual pendiente.',
  signalIds: ['sig_aapl_negative', 'sig_btc_uncertain', 'sig_wti_context'], pending: 2, reviewed: 1,
}

export const auditRun = {
  id: 'run_phase0_fixture_001', status: 'completed', node: 'pending_review', model: 'fixture-deterministic', prompt: 'phase0-v1', retryCount: 0,
  startedAt: '2026-07-11T10:00:00Z', finishedAt: '2026-07-11T12:00:00Z', snapshots: 10,
  steps: [
    { name: 'Ingesta de fuentes', status: 'completed', detail: '6 snapshots de noticias capturados' },
    { name: 'Resolución de eventos', status: 'completed', detail: '3 eventos normalizados' },
    { name: 'Cálculo de mercado', status: 'completed', detail: '4 series evaluadas' },
    { name: 'Construcción de señales', status: 'completed', detail: '3 señales con evidencia enlazada' },
    { name: 'Control humano', status: 'pending', detail: '2 señales requieren revisión' },
  ],
}
