import {
  fixtureMeta, sources, assets, events, articles, signals, evidence, briefing, auditRun,
} from './data.js'

const app = document.querySelector('#app')
const storageKey = 'nexomercado-finance-prototype-v1'
const defaultState = {
  theme: 'light', assistantOpen: true, navOpen: false, radarFilter: 'all', signalFilter: 'all',
  reviews: Object.fromEntries(signals.map(signal => [signal.id, signal.reviewStatus])),
  localBriefings: [],
  messages: [
    { role: 'assistant', text: 'Estoy en modo demostración. Puedo orientarte entre señales, fuentes y revisiones sin generar datos financieros nuevos.' },
  ],
}

let state = loadState()
let searchOpen = false

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}')
    const requestedTheme = new URLSearchParams(location.search).get('theme')
    return {
      ...defaultState,
      ...saved,
      ...(requestedTheme === 'dark' || requestedTheme === 'light' ? { theme: requestedTheme } : {}),
      reviews: { ...defaultState.reviews, ...(saved.reviews || {}) },
    }
  } catch {
    return structuredClone(defaultState)
  }
}

function saveState() {
  localStorage.setItem(storageKey, JSON.stringify(state))
}

function setState(patch) {
  state = { ...state, ...patch }
  saveState()
  render()
}

function currentPath() {
  return (location.hash.replace(/^#\/?/, '') || 'summary').split('?')[0]
}

function routeTo(path) {
  location.hash = `#/${path}`
  state.navOpen = false
  searchOpen = false
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character])
}

const fmtMoney = (value, currency = 'USD') => new Intl.NumberFormat('es-EC', { style: 'currency', currency, maximumFractionDigits: value > 10000 ? 0 : 2 }).format(value)
const fmtPercent = value => value == null ? '—' : `${value > 0 ? '+' : ''}${new Intl.NumberFormat('es-EC', { style: 'percent', maximumFractionDigits: 1 }).format(value)}`
const fmtDate = value => new Intl.DateTimeFormat('es-EC', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }).format(new Date(value))
const sourceById = id => sources.find(source => source.id === id)
const assetBySymbol = symbol => assets.find(asset => asset.symbol === decodeURIComponent(symbol)) || assets[0]
const signalById = id => signals.find(signal => signal.id === id) || signals[0]
const eventById = id => events.find(event => event.id === id)
const currentReview = signal => state.reviews[signal.id] || signal.reviewStatus

function icon(name) {
  const paths = {
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    search: '<circle cx="11" cy="11" r="6"/><path d="m16 16 4 4"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/>',
    panel: '<path d="M4 5h16v14H4zM15 5v14"/>',
    reset: '<path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.6M4 4v4.6h4.6"/>',
    arrow: '<path d="m9 18 6-6-6-6"/>',
    close: '<path d="m6 6 12 12M18 6 6 18"/>',
    send: '<path d="m4 4 17 8-17 8 3-8-3-8Zm3 8h14"/>',
  }
  return `<svg aria-hidden="true" viewBox="0 0 24 24">${paths[name] || paths.arrow}</svg>`
}

function sparkline(values, tone = 'positive', large = false) {
  const width = large ? 720 : 180
  const height = large ? 220 : 64
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = max - min || 1
  const points = values.map((value, index) => {
    const x = (index / Math.max(1, values.length - 1)) * width
    const y = height - 8 - ((value - min) / spread) * (height - 16)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return `<svg class="sparkline ${large ? 'sparkline--large' : ''}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Serie verificable de ${values.length} observaciones"><line x1="0" y1="${height - 8}" x2="${width}" y2="${height - 8}" class="chart-baseline"/><polyline points="${points}" class="chart-line chart-line--${tone}"/></svg>`
}

function badge(value, label) {
  const normalized = value.replace('_', '-')
  const names = {
    negative: 'Negativa', positive: 'Positiva', uncertain: 'Incierta', neutral: 'Neutral',
    reviewed: 'Revisada', 'pending-review': 'Pendiente', escalated: 'Escalada', discarded: 'Descartada',
    completed: 'Completada', pending: 'Pendiente', draft: 'Borrador', fixture: 'Fixture',
  }
  return `<span class="badge badge--${normalized}">${escapeHtml(label || names[normalized] || value)}</span>`
}

function pageHeading(eyebrow, title, description, actions = '') {
  return `<header class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p>${description}</p></div>${actions ? `<div class="page-actions">${actions}</div>` : ''}</header>`
}

function sectionHeading(kicker, title, action = '') {
  return `<div class="section-heading"><div><span>${kicker}</span><h2>${title}</h2></div>${action}</div>`
}

function dataStamp() {
  return `<div class="data-stamp" role="note"><span class="status-dot"></span><strong>${fixtureMeta.fixtureId}</strong><span>${fixtureMeta.providerLabel}</span><span>corte ${fmtDate(fixtureMeta.clock)}</span></div>`
}

function navItem(path, number, label) {
  const active = currentPath() === path || currentPath().startsWith(`${path}/`)
  return `<button class="nav-item ${active ? 'is-active' : ''}" data-route="${path}" type="button"><span>${number}</span><strong>${label}</strong></button>`
}

function shell(content) {
  const path = currentPath()
  document.documentElement.dataset.theme = state.theme
  document.documentElement.style.colorScheme = state.theme
  return `
    <div class="prototype-shell ${state.assistantOpen && path !== 'assistant' ? 'has-assistant' : ''}">
      <header class="topbar">
        <button class="icon-button mobile-only" data-action="nav-toggle" aria-label="Abrir navegación">${icon('menu')}</button>
        <button class="brand" data-route="summary" aria-label="Ir a Panorama"><span class="brand-mark">N</span><span><strong>NexoMercado</strong><small>FINANCE · CONCEPTO</small></span></button>
        <form class="global-search" id="global-search" role="search">
          ${icon('search')}<input id="search-input" type="search" autocomplete="off" placeholder="Buscar activo, señal o evento" aria-label="Buscar activo, señal o evento" aria-expanded="${searchOpen}" />
          <kbd>⌘ K</kbd>
          <div class="search-results" id="search-results" ${searchOpen ? '' : 'hidden'}></div>
        </form>
        <div class="topbar-actions">
          <button class="icon-button" data-action="theme" aria-label="Cambiar a tema ${state.theme === 'light' ? 'oscuro' : 'claro'}">${icon(state.theme === 'light' ? 'moon' : 'sun')}</button>
          <button class="icon-button desktop-only ${state.assistantOpen ? 'is-active' : ''}" data-action="assistant-toggle" aria-label="Alternar asistente">${icon('panel')}</button>
          <button class="avatar-button" aria-label="Cuenta de Analista Demo">AD</button>
        </div>
      </header>

      <aside class="sidebar ${state.navOpen ? 'is-open' : ''}" aria-label="Navegación principal">
        <button class="icon-button nav-close mobile-only" data-action="nav-toggle" aria-label="Cerrar navegación">${icon('close')}</button>
        <p class="nav-label">Mercado</p>
        ${navItem('summary', '01', 'Panorama')}
        <p class="nav-label">Investigación</p>
        ${navItem('radar', '02', 'Radar')}
        ${navItem('signals', '03', 'Señales')}
        <p class="nav-label">Operaciones</p>
        ${navItem('reviews', '04', 'Revisión')}
        ${navItem('briefings', '05', 'Briefings')}
        <p class="nav-label">Control</p>
        ${navItem('audit', '06', 'Auditoría')}
        <div class="sidebar-foot">
          ${badge('fixture')}
          <p>Schema ${fixtureMeta.schemaVersion}<br/>Sin conexión al backend</p>
          <button class="text-button" data-action="reset">${icon('reset')} Restaurar demo</button>
        </div>
      </aside>
      <div class="nav-backdrop ${state.navOpen ? 'is-visible' : ''}" data-action="nav-toggle"></div>

      <main id="main-content" class="workspace" tabindex="-1">${content}</main>
      ${path !== 'assistant' ? assistantRail() : ''}
      ${mobileNav()}
    </div>`
}

function mobileNav() {
  return `<nav class="mobile-nav" aria-label="Navegación móvil">
    <button data-route="summary" class="${currentPath() === 'summary' ? 'is-active' : ''}"><span>01</span>Inicio</button>
    <button data-route="radar" class="${currentPath() === 'radar' ? 'is-active' : ''}"><span>02</span>Radar</button>
    <button data-route="reviews" class="${currentPath() === 'reviews' ? 'is-active' : ''}"><span>04</span>Revisar</button>
    <button data-route="assistant" class="${currentPath() === 'assistant' ? 'is-active' : ''}"><span>AI</span>Consultar</button>
  </nav>`
}

function assistantRail() {
  if (!state.assistantOpen) return ''
  return `<aside class="assistant-rail" aria-label="Asistente contextual">
    <div class="assistant-head"><div><p class="eyebrow">Asistente contextual</p><h2>Investigación</h2></div><button class="icon-button" data-action="assistant-toggle" aria-label="Cerrar asistente">${icon('close')}</button></div>
    <div class="context-chip"><span>Contexto</span><strong>${contextLabel()}</strong></div>
    ${chatBody()}
  </aside>`
}

function contextLabel() {
  const path = currentPath()
  if (path.startsWith('signal/')) return signalById(path.split('/')[1]).symbol
  if (path.startsWith('asset/')) return assetBySymbol(path.split('/')[1]).symbol
  return ({ summary: 'Panorama', radar: 'Radar', signals: 'Señales', reviews: 'Revisión', briefings: 'Briefings', audit: 'Auditoría' })[path] || 'NexoMercado'
}

function chatBody() {
  return `<div class="chat-log" aria-live="polite">${state.messages.map(message => `<div class="chat-message chat-message--${message.role}"><span>${message.role === 'assistant' ? 'NEXO' : 'TÚ'}</span><p>${escapeHtml(message.text)}</p></div>`).join('')}</div>
    <form class="chat-composer" id="chat-form"><label for="chat-input">Pregunta sobre el contexto visible</label><textarea id="chat-input" rows="3" placeholder="¿Qué evidencia necesita revisión?"></textarea><div><small>Respuesta simulada · sin asesoría</small><button class="icon-button" type="submit" aria-label="Enviar pregunta">${icon('send')}</button></div></form>`
}

function marketCard(asset) {
  const first = asset.values[0]
  const last = asset.values.at(-1)
  const change = (last - first) / first
  const tone = change < 0 ? 'negative' : 'positive'
  return `<button class="market-card" data-route="asset/${encodeURIComponent(asset.symbol)}" type="button">
    <div class="market-card-head"><div><strong>${asset.symbol}</strong><span>${asset.name}</span></div><span class="change change--${tone}">${fmtPercent(change)}</span></div>
    <div class="market-value"><strong>${fmtMoney(last, asset.currency)}</strong><small>${asset.values.length} observaciones</small></div>
    ${sparkline(asset.values, tone)}
  </button>`
}

function signalRow(signal) {
  const status = currentReview(signal)
  return `<button class="table-row signal-row signal-grid" data-route="signal/${signal.id}" type="button">
    <span class="asset-cell"><strong>${signal.symbol}</strong><small>${signal.assetName}</small></span>
    <span>${badge(signal.impact)}</span><span class="numeric">${Math.round(signal.confidence * 100)}%</span>
    <span>${badge(status)}</span><span class="row-thesis">${signal.thesis}</span><span class="row-arrow">${icon('arrow')}</span>
  </button>`
}

function evidenceLedger(signalId, compact = false) {
  const items = evidence.filter(item => item.signalId === signalId)
  return `<div class="evidence-ledger ${compact ? 'evidence-ledger--compact' : ''}">
    ${items.map((item, index) => {
      const source = sourceById(item.sourceId)
      return `<article class="ledger-entry ${item.supports ? '' : 'is-counter'}"><div class="ledger-index">${String(index + 1).padStart(2, '0')}</div><div><div class="ledger-meta"><span>${item.type}</span>${source ? `<span>${source.name}</span><span>Tier ${source.tier}</span>` : '<span>Cálculo reproducible</span>'}</div><p>${item.text}</p></div><span class="ledger-state">${item.supports ? 'SOPORTA' : 'CONTRADICE'}</span></article>`
    }).join('')}
  </div>`
}

function renderSummary() {
  const reviewed = signals.filter(signal => currentReview(signal) === 'reviewed').length
  return `${pageHeading('01 · Panorama', 'Mercado, contexto y decisiones', 'Una vista compacta de los datos disponibles y del trabajo humano pendiente.', `<button class="primary-button" data-route="radar">Explorar radar ${icon('arrow')}</button>`)}
    ${dataStamp()}
    <section class="market-strip" aria-label="Activos del fixture">${assets.map(marketCard).join('')}</section>
    <div class="dashboard-grid">
      <div class="primary-column">
        <section class="panel">${sectionHeading('Señales priorizadas', 'Decisiones con evidencia', `<button class="text-button" data-route="signals">Ver todas ${icon('arrow')}</button>`)}<div class="table-head signal-grid"><span>Activo</span><span>Impacto</span><span>Conf.</span><span>Revisión</span><span>Tesis</span><span></span></div>${signals.map(signalRow).join('')}</section>
        <section class="panel">${sectionHeading('Radar', 'Eventos relevantes', `<button class="text-button" data-route="radar">Abrir radar ${icon('arrow')}</button>`)}<div class="news-list">${events.map(eventCard).join('')}</div></section>
      </div>
      <aside class="secondary-column">
        <section class="panel review-meter">${sectionHeading('Control humano', 'Estado de revisión')}<strong class="hero-number">${reviewed}<small>/ ${signals.length}</small></strong><p>señales verificadas</p><div class="meter"><span style="width:${reviewed / signals.length * 100}%"></span></div><button class="secondary-button" data-route="reviews">Revisar ${signals.length - reviewed} pendientes</button></section>
        <section class="panel">${sectionHeading('Ledger activo', 'Por qué confiar')}<p class="panel-copy">Cada tesis mantiene visibles sus fuentes, cálculos, contraevidencia y estado humano.</p>${evidenceLedger('sig_btc_uncertain', true)}<button class="text-button" data-route="signal/sig_btc_uncertain">Resolver contradicción ${icon('arrow')}</button></section>
      </aside>
    </div>`
}

function eventCard(event) {
  const relatedSignal = signalById(event.signalId)
  return `<button class="news-row" data-route="signal/${event.signalId}" type="button"><div class="news-time"><strong>${fmtDate(event.time)}</strong><span>${event.articleIds.length} fuentes</span></div><div><div class="news-meta"><span>${event.symbol}</span>${badge(relatedSignal.impact)}</div><h3>${event.title}</h3><p>${event.summary}</p></div><span class="row-arrow">${icon('arrow')}</span></button>`
}

function renderRadar() {
  const filtered = events.filter(event => state.radarFilter === 'all' || (state.radarFilter === 'contradiction' ? event.id.includes('btc') : !event.id.includes('btc')))
  return `${pageHeading('02 · Investigación', 'Radar de eventos', 'Agrupa cobertura corroborada y contradicciones antes de convertirlas en señales.')}
    ${dataStamp()}
    <div class="filter-bar" role="group" aria-label="Filtrar eventos">
      ${filterButton('radar', 'all', 'Todos', events.length)}${filterButton('radar', 'corroborated', 'Corroborados', 2)}${filterButton('radar', 'contradiction', 'Con contradicción', 1)}
    </div>
    <section class="panel">${sectionHeading('Monitor', `${filtered.length} eventos visibles`)}<div class="radar-list">${filtered.map(event => {
      const relatedArticles = event.articleIds.map(id => articles.find(article => article.id === id))
      return `<article class="radar-event"><div class="radar-marker"></div><div class="radar-event-main"><div class="news-meta"><span>${event.symbol}</span><span>${fmtDate(event.time)}</span>${event.id.includes('btc') ? badge('uncertain', 'Contradicción') : badge('positive', 'Corroborado')}</div><h2>${event.title}</h2><p>${event.summary}</p><div class="source-stack">${relatedArticles.map(article => `<div><strong>${sourceById(article.sourceId).name}</strong><span>${fmtDate(article.publishedAt)}</span><p>${article.headline}</p></div>`).join('')}</div></div><button class="secondary-button" data-route="signal/${event.signalId}">Abrir señal</button></article>`
    }).join('')}</div></section>`
}

function filterButton(group, value, label, count) {
  const active = state[`${group}Filter`] === value
  return `<button class="filter-button ${active ? 'is-active' : ''}" data-filter-group="${group}" data-filter-value="${value}" type="button">${label}<span>${count}</span></button>`
}

function renderAsset(symbol) {
  const asset = assetBySymbol(symbol)
  const first = asset.values[0]
  const last = asset.values.at(-1)
  const change = (last - first) / first
  const relatedSignal = signals.find(signal => signal.symbol === asset.symbol)
  return `<button class="back-button" data-route="summary">← Volver al panorama</button>
    ${pageHeading(`${asset.type} · ${asset.exchange}`, `${asset.symbol} · ${asset.name}`, `Serie procedente de ${asset.provider}; se muestra únicamente el rango disponible en el fixture.`, relatedSignal ? `<button class="primary-button" data-route="signal/${relatedSignal.id}">Ver señal ${icon('arrow')}</button>` : '')}
    ${dataStamp()}
    <div class="asset-layout"><section class="panel asset-chart-panel"><div class="asset-quote"><div><strong>${fmtMoney(last, asset.currency)}</strong><span class="change change--${change < 0 ? 'negative' : 'positive'}">${fmtPercent(change)} en el rango</span></div><div><span>Proveedor</span><strong>${asset.provider}</strong><span>Recuperado</span><strong>${fmtDate(asset.retrievedAt)}</strong></div></div>${sparkline(asset.values, change < 0 ? 'negative' : 'positive', true)}<div class="chart-caption"><span>${asset.values.length} observaciones</span><span>Inicio ${fmtMoney(first)}</span><span>Fin ${fmtMoney(last)}</span></div></section>
    <aside class="panel">${sectionHeading('Ficha', 'Procedencia')}<dl class="detail-list"><div><dt>Instrumento</dt><dd>${asset.type}</dd></div><div><dt>Moneda</dt><dd>${asset.currency}</dd></div><div><dt>Mercado</dt><dd>${asset.exchange}</dd></div><div><dt>Modo</dt><dd>Fixture</dd></div></dl>${relatedSignal ? `<hr/>${sectionHeading('Señal asociada', `${Math.round(relatedSignal.confidence * 100)}% confianza`)}<p class="panel-copy">${relatedSignal.thesis}</p>${badge(relatedSignal.impact)} ${badge(currentReview(relatedSignal))}` : '<p>No existe una señal asociada en este fixture.</p>'}</aside></div>`
}

function renderSignals() {
  const filtered = signals.filter(signal => state.signalFilter === 'all' || currentReview(signal) === state.signalFilter)
  return `${pageHeading('03 · Investigación', 'Señales explicables', 'Cada señal une tesis, reacción de mercado, evidencia, límites y decisión humana.')}${dataStamp()}
    <div class="filter-bar" role="group" aria-label="Filtrar señales">${filterButton('signal', 'all', 'Todas', signals.length)}${filterButton('signal', 'pending_review', 'Pendientes', signals.filter(signal => currentReview(signal) === 'pending_review').length)}${filterButton('signal', 'reviewed', 'Revisadas', signals.filter(signal => currentReview(signal) === 'reviewed').length)}</div>
    <section class="panel"><div class="table-head signal-grid"><span>Activo</span><span>Impacto</span><span>Conf.</span><span>Revisión</span><span>Tesis</span><span></span></div>${filtered.map(signalRow).join('')}</section>`
}

function renderSignalDetail(id) {
  const signal = signalById(id)
  const event = eventById(signal.eventId)
  const review = currentReview(signal)
  const metricItems = [
    ['Retorno activo', fmtPercent(signal.metrics.assetReturn)], ['Benchmark', fmtPercent(signal.metrics.benchmarkReturn)],
    ['Retorno anormal', fmtPercent(signal.metrics.abnormalReturn)], ['Volumen relativo', signal.metrics.relativeVolume ? `${signal.metrics.relativeVolume.toFixed(1)}×` : '—'],
  ]
  return `<button class="back-button" data-route="signals">← Volver a señales</button>
    ${pageHeading(`${signal.symbol} · ${event.title}`, 'Tesis y cadena de evidencia', signal.thesis, `<button class="secondary-button" data-route="asset/${encodeURIComponent(signal.symbol)}">Ver activo</button>`)}
    ${dataStamp()}
    <div class="signal-summary-bar"><div><span>Impacto</span>${badge(signal.impact)}</div><div><span>Confianza</span><strong>${Math.round(signal.confidence * 100)}%</strong></div><div><span>Revisión</span>${badge(review)}</div><div><span>Evidencias</span><strong>${evidence.filter(item => item.signalId === signal.id).length}</strong></div></div>
    <div class="detail-grid"><div class="primary-column">
      <section class="panel">${sectionHeading('01 · Reacción', 'Lectura de mercado')}<div class="metric-grid">${metricItems.map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join('')}</div></section>
      <section class="panel">${sectionHeading('02 · Ledger', 'Evidencia enlazada')} ${evidenceLedger(signal.id)}</section>
      <section class="panel two-up"><div>${sectionHeading('03 · Límite', 'Qué invalidaría la tesis')}<ul>${signal.invalidation.map(item => `<li>${item}</li>`).join('')}</ul></div><div>${sectionHeading('04 · Siguiente paso', 'Investigación sugerida')}<p>${signal.nextAction}</p></div></section>
    </div><aside class="secondary-column"><section class="panel review-console">${sectionHeading('Decisión humana', review === 'reviewed' ? 'Señal verificada' : 'Revisión pendiente')}<p>Esta acción solo cambia el estado local del prototipo.</p><div class="review-actions"><button data-review-id="${signal.id}" data-review-status="reviewed" class="secondary-button ${review === 'reviewed' ? 'is-selected' : ''}">Aprobar</button><button data-review-id="${signal.id}" data-review-status="escalated" class="secondary-button ${review === 'escalated' ? 'is-selected' : ''}">Escalar</button><button data-review-id="${signal.id}" data-review-status="discarded" class="secondary-button ${review === 'discarded' ? 'is-selected' : ''}">Descartar</button></div><label for="review-note">Justificación</label><textarea id="review-note" rows="4" placeholder="La evidencia y los cálculos fueron verificados."></textarea><small>Analista Demo · estado local</small></section><section class="panel disclaimer"><strong>Uso responsable</strong><p>${signal.disclaimer}</p></section></aside></div>`
}

function renderReviews() {
  const pending = signals.filter(signal => currentReview(signal) === 'pending_review')
  const resolved = signals.filter(signal => currentReview(signal) !== 'pending_review')
  return `${pageHeading('04 · Operaciones', 'Cola de revisión', 'Prioriza contradicciones y decisiones que requieren justificación humana.')}${dataStamp()}
    <div class="review-kpis"><div><strong>${pending.length}</strong><span>Pendientes</span></div><div><strong>${resolved.length}</strong><span>Resueltas</span></div><div><strong>1</strong><span>Con contradicción</span></div></div>
    <section class="panel">${sectionHeading('Prioridad', 'Requieren acción')}<div class="review-list">${pending.length ? pending.map(reviewCard).join('') : '<div class="empty-state"><strong>Cola resuelta</strong><p>Restaura la demo para volver al estado inicial.</p></div>'}</div></section>
    <section class="panel">${sectionHeading('Historial local', 'Decisiones registradas')}<div class="review-list">${resolved.map(reviewCard).join('')}</div></section>`
}

function reviewCard(signal) {
  const signalEvidence = evidence.filter(item => item.signalId === signal.id)
  const contradictions = signalEvidence.filter(item => !item.supports).length
  return `<button class="review-card" data-route="signal/${signal.id}" type="button"><div class="priority-code">${contradictions ? 'P0' : 'P1'}</div><div><div class="news-meta"><span>${signal.symbol}</span>${badge(signal.impact)}${badge(currentReview(signal))}</div><h3>${signal.thesis}</h3><p>${signalEvidence.length} evidencias · ${contradictions} contradicciones · ${Math.round(signal.confidence * 100)}% confianza</p></div><span class="row-arrow">${icon('arrow')}</span></button>`
}

function renderBriefings() {
  const items = [briefing, ...state.localBriefings]
  return `${pageHeading('05 · Operaciones', 'Briefings', 'Convierte señales revisadas en una lectura ejecutiva con límites visibles.', `<button class="primary-button" data-action="create-briefing">Crear desde señales</button>`)}${dataStamp()}
    <section class="panel">${sectionHeading('Colección', `${items.length} briefings`)}<div class="briefing-grid">${items.map(item => `<button class="briefing-card" data-route="briefing/${item.id}" type="button"><div class="document-code">BRF</div><div class="news-meta">${badge(item.status)}<span>${fmtDate(item.updatedAt)}</span></div><h2>${item.name}</h2><p>${item.summary}</p><div class="briefing-foot"><span>${item.signalIds.length} señales</span><span>${item.pending} pendientes</span>${icon('arrow')}</div></button>`).join('')}</div></section>`
}

function renderBriefingDetail(id) {
  const item = [briefing, ...state.localBriefings].find(candidate => candidate.id === id) || briefing
  const itemSignals = item.signalIds.map(signalById)
  return `<button class="back-button" data-route="briefings">← Volver a briefings</button>${pageHeading(`Briefing · ${item.name}`, 'Lectura ejecutiva', item.summary, `<button class="secondary-button" data-action="copy-briefing">Copiar resumen</button>`)}${dataStamp()}
    <div class="briefing-detail"><section class="briefing-paper"><header><span>NEXOMERCADO · INTELIGENCIA VERIFICABLE</span><span>${fmtDate(item.updatedAt)}</span></header><h1>${item.name}</h1><p class="briefing-lead">${item.summary}</p><div class="briefing-rule"></div>${itemSignals.map((signal, index) => `<article><span class="briefing-number">0${index + 1}</span><div><div class="news-meta"><span>${signal.symbol}</span>${badge(signal.impact)}${badge(currentReview(signal))}</div><h2>${signal.thesis}</h2><p><strong>Siguiente verificación:</strong> ${signal.nextAction}</p></div></article>`).join('')}<footer>${signals[0].disclaimer}</footer></section><aside class="panel">${sectionHeading('Control editorial', 'Antes de compartir')}<dl class="detail-list"><div><dt>Estado</dt><dd>${badge(item.status)}</dd></div><div><dt>Señales</dt><dd>${itemSignals.length}</dd></div><div><dt>Pendientes</dt><dd>${itemSignals.filter(signal => currentReview(signal) === 'pending_review').length}</dd></div><div><dt>Revisadas</dt><dd>${itemSignals.filter(signal => currentReview(signal) === 'reviewed').length}</dd></div></dl><p class="panel-copy">El briefing permanece como borrador mientras existan señales pendientes.</p></aside></div>`
}

function renderAudit() {
  return `${pageHeading('06 · Control', 'Auditoría de ejecuciones', 'Expone modelo, prompt, fuentes, pasos y estado final del workflow.')}${dataStamp()}
    <section class="panel"><div class="audit-table-head"><span>Run</span><span>Estado</span><span>Modelo</span><span>Duración</span><span>Snapshots</span><span></span></div><button class="audit-row" data-route="audit/${auditRun.id}"><span><strong>${auditRun.id}</strong><small>${fmtDate(auditRun.startedAt)}</small></span>${badge(auditRun.status)}<span class="mono">${auditRun.model}</span><span class="numeric">2h 00m</span><span class="numeric">${auditRun.snapshots}</span>${icon('arrow')}</button></section>`
}

function renderAuditDetail() {
  return `<button class="back-button" data-route="audit">← Volver a auditoría</button>${pageHeading('Ejecución reproducible', auditRun.id, 'La trazabilidad técnica se presenta como una secuencia legible, no como un volcado de sistema.')}${dataStamp()}
    <div class="audit-detail"><section class="panel">${sectionHeading('Timeline', 'Pasos del workflow')}<div class="run-timeline">${auditRun.steps.map((step, index) => `<article><span class="timeline-node ${step.status}">${String(index + 1).padStart(2, '0')}</span><div><div class="news-meta">${badge(step.status)}<span>${index < 4 ? 'Completado' : 'Requiere operador'}</span></div><h3>${step.name}</h3><p>${step.detail}</p></div></article>`).join('')}</div></section><aside class="panel">${sectionHeading('Metadatos', 'Reproducibilidad')}<dl class="detail-list"><div><dt>Modelo</dt><dd>${auditRun.model}</dd></div><div><dt>Prompt</dt><dd>${auditRun.prompt}</dd></div><div><dt>Reintentos</dt><dd>${auditRun.retryCount}</dd></div><div><dt>Inicio</dt><dd>${fmtDate(auditRun.startedAt)}</dd></div><div><dt>Fin</dt><dd>${fmtDate(auditRun.finishedAt)}</dd></div><div><dt>Snapshots</dt><dd>${auditRun.snapshots}</dd></div></dl><div class="hash-block"><span>INPUT HASH</span><code>sha256:c7dd23...53cf5c</code></div></aside></div>`
}

function renderAssistantPage() {
  return `${pageHeading('Asistente', 'Investiga con el contexto visible', 'La demo muestra el flujo conversacional sin llamar a un modelo ni crear afirmaciones financieras.')}${dataStamp()}<section class="assistant-page"><div class="assistant-page-intro"><span class="brand-mark brand-mark--large">N</span><h2>¿Qué quieres verificar?</h2><p>Prueba una pregunta sobre las señales, las contradicciones o la revisión pendiente.</p><div class="prompt-list"><button data-prompt="¿Qué señal tiene contraevidencia?">¿Qué señal tiene contraevidencia?</button><button data-prompt="¿Qué falta revisar?">¿Qué falta revisar?</button><button data-prompt="Resume el estado del fixture">Resume el estado del fixture</button></div></div><div class="assistant-page-chat">${chatBody()}</div></section>`
}

function renderContent() {
  const [page, id] = currentPath().split('/')
  const renderers = {
    summary: renderSummary, radar: renderRadar, asset: () => renderAsset(id), signals: renderSignals,
    signal: () => renderSignalDetail(id), reviews: renderReviews, briefings: renderBriefings,
    briefing: () => renderBriefingDetail(id), audit: () => id ? renderAuditDetail(id) : renderAudit(), assistant: renderAssistantPage,
  }
  return (renderers[page] || renderSummary)()
}

function render() {
  app.innerHTML = shell(renderContent())
  bindSearch()
  requestAnimationFrame(() => document.querySelector('.workspace')?.classList.add('is-ready'))
}

function bindSearch() {
  const input = document.querySelector('#search-input')
  if (!input) return
  input.addEventListener('input', () => showSearchResults(input.value))
  input.addEventListener('focus', () => showSearchResults(input.value))
}

function showSearchResults(query = '') {
  const resultBox = document.querySelector('#search-results')
  if (!resultBox) return
  const normalized = query.trim().toLowerCase()
  const matches = [
    ...assets.map(asset => ({ type: 'Activo', title: `${asset.symbol} · ${asset.name}`, path: `asset/${encodeURIComponent(asset.symbol)}` })),
    ...signals.map(signal => ({ type: 'Señal', title: `${signal.symbol} · ${signal.thesis}`, path: `signal/${signal.id}` })),
    ...events.map(event => ({ type: 'Evento', title: event.title, path: `signal/${event.signalId}` })),
  ].filter(item => !normalized || item.title.toLowerCase().includes(normalized)).slice(0, 6)
  searchOpen = true
  resultBox.hidden = false
  resultBox.innerHTML = matches.length ? matches.map(item => `<button data-route="${item.path}" type="button"><span>${item.type}</span><strong>${item.title}</strong></button>`).join('') : '<p>Sin coincidencias en el fixture.</p>'
  document.querySelector('#search-input')?.setAttribute('aria-expanded', 'true')
}

app.addEventListener('click', event => {
  const route = event.target.closest('[data-route]')?.dataset.route
  if (route) return routeTo(route)
  const action = event.target.closest('[data-action]')?.dataset.action
  if (action === 'theme') return setState({ theme: state.theme === 'light' ? 'dark' : 'light' })
  if (action === 'assistant-toggle') return setState({ assistantOpen: !state.assistantOpen })
  if (action === 'nav-toggle') return setState({ navOpen: !state.navOpen })
  if (action === 'reset') {
    localStorage.removeItem(storageKey)
    state = structuredClone(defaultState)
    searchOpen = false
    return render()
  }
  if (action === 'create-briefing') {
    const stamp = new Date().toISOString()
    const localItem = { ...briefing, id: `brf_local_${Date.now()}`, name: `Demo Global · copia local`, updatedAt: stamp, summary: briefing.summary }
    return setState({ localBriefings: [localItem, ...state.localBriefings] })
  }
  if (action === 'copy-briefing') {
    navigator.clipboard?.writeText(briefing.summary)
    const button = event.target.closest('button')
    button.textContent = 'Resumen copiado'
  }
  const filter = event.target.closest('[data-filter-group]')
  if (filter) return setState({ [`${filter.dataset.filterGroup}Filter`]: filter.dataset.filterValue })
  const reviewButton = event.target.closest('[data-review-id]')
  if (reviewButton) return setState({ reviews: { ...state.reviews, [reviewButton.dataset.reviewId]: reviewButton.dataset.reviewStatus } })
  const prompt = event.target.closest('[data-prompt]')?.dataset.prompt
  if (prompt) submitChat(prompt)
})

app.addEventListener('submit', event => {
  event.preventDefault()
  if (event.target.id === 'global-search') {
    const first = document.querySelector('#search-results [data-route]')
    if (first) routeTo(first.dataset.route)
  }
  if (event.target.id === 'chat-form') {
    const input = event.target.querySelector('textarea')
    if (input.value.trim()) submitChat(input.value.trim())
  }
})

function submitChat(text) {
  const normalized = text.toLowerCase()
  let response = 'Consulta registrada en modo demostración. El prototipo no ejecuta un modelo ni añade afirmaciones fuera del fixture.'
  if (normalized.includes('contra')) response = 'BTC-USD tiene una fuente que soporta la aprobación y otra que afirma que la medida sigue en consulta; por eso permanece incierta.'
  if (normalized.includes('revis')) response = `${signals.filter(signal => currentReview(signal) === 'pending_review').length} señales permanecen pendientes de revisión humana en el estado local.`
  if (normalized.includes('fixture') || normalized.includes('resume')) response = 'El fixture contiene 4 activos, 3 eventos, 3 señales, 12 evidencias, 1 briefing base y 1 ejecución auditable.'
  setState({ messages: [...state.messages, { role: 'user', text }, { role: 'assistant', text: response }] })
}

window.addEventListener('hashchange', render)
window.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    document.querySelector('#search-input')?.focus()
  }
  if (event.key === 'Escape' && searchOpen) {
    searchOpen = false
    const results = document.querySelector('#search-results')
    if (results) results.hidden = true
    document.querySelector('#search-input')?.setAttribute('aria-expanded', 'false')
  }
})

render()
