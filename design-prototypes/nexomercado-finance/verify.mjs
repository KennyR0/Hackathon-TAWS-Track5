import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const root = fileURLToPath(new URL('.', import.meta.url))
const baseUrl = 'http://127.0.0.1:4175/'
const debuggingPort = 9337
const browserPath = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean).find(existsSync)
const captureBrowserPath = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  browserPath,
].filter(Boolean).find(existsSync)

if (!browserPath) throw new Error('No se encontró Chrome o Edge. Define CHROME_PATH.')

const server = spawn(process.execPath, ['server.mjs'], { cwd: root, stdio: 'ignore' })
const profile = join(process.env.TEMP || root, `nexo-verify-${Date.now()}`)
const browser = spawn(browserPath, [
  '--headless=new', '--no-first-run', '--disable-extensions', '--hide-scrollbars',
  `--remote-debugging-port=${debuggingPort}`, `--user-data-dir=${profile}`, 'about:blank',
], { stdio: 'ignore' })

const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))
const failures = []
const browserErrors = []
const assert = (condition, message) => { if (!condition) failures.push(message) }

async function waitFor(url, attempts = 40) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url)
      if (response.ok) return response
    } catch {}
    await sleep(150)
  }
  throw new Error(`Timeout esperando ${url}`)
}

await waitFor(baseUrl)
const pages = await (await waitFor(`http://127.0.0.1:${debuggingPort}/json/list`)).json()
const targetPage = pages.find(page => page.type === 'page' && !page.url.startsWith('chrome-extension://'))
if (!targetPage) throw new Error('No se encontró una pestaña navegable en el navegador headless.')
const socket = new WebSocket(targetPage.webSocketDebuggerUrl)
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true })
  socket.addEventListener('error', reject, { once: true })
})

let messageId = 0
const pending = new Map()
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    message.error ? reject(new Error(message.error.message)) : resolve(message.result)
  }
  if (message.method === 'Runtime.exceptionThrown') {
    const details = message.params.exceptionDetails
    browserErrors.push(details.exception?.description || `${details.text} @ ${details.url || 'inline'}:${details.lineNumber || 0}`)
  }
  if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error') browserErrors.push(message.params.entry.text)
})

function send(method, params = {}) {
  const id = ++messageId
  socket.send(JSON.stringify({ id, method, params }))
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id)
      reject(new Error(`Timeout CDP: ${method}`))
    }, 8000)
    pending.set(id, {
      resolve: value => { clearTimeout(timer); resolve(value) },
      reject: error => { clearTimeout(timer); reject(error) },
    })
  })
}

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text)
  return result.result.value
}

const viewport = (width, height, mobile = false) => send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile, screenWidth: width, screenHeight: height })

async function navigate(path, theme = 'light') {
  await send('Page.navigate', { url: `${baseUrl}?theme=${theme}#/${path}` })
  for (let attempt = 0; attempt < 30; attempt += 1) {
    await sleep(100)
    const ready = await evaluate(`location.hash === '#/${path}' && Boolean(document.querySelector('.workspace h1'))`)
    if (ready) return
  }
  const diagnostic = await evaluate(`({ href: location.href, hash: location.hash, title: document.title, app: document.querySelector('#app')?.innerHTML.slice(0, 160), errors: document.body?.innerText.slice(0, 160) })`)
  throw new Error(`La vista ${path} no terminó de renderizar: ${JSON.stringify(diagnostic)}`)
}

async function capture(name, width, height, mobile, theme) {
  await mkdir(join(root, 'screenshots'), { recursive: true })
  if (!mobile) {
    const screenshotPath = join(root, 'screenshots', `${name}.png`)
    const captureProfile = join(process.env.TEMP || root, `nexo-capture-${name}-${Date.now()}`)
    const exitCode = await new Promise((resolve, reject) => {
      const process = spawn(captureBrowserPath, [
        '--headless=new', '--no-first-run', '--disable-extensions', '--hide-scrollbars',
        '--run-all-compositor-stages-before-draw', `--user-data-dir=${captureProfile}`,
        `--window-size=${width},${height}`, '--virtual-time-budget=1800',
        `--screenshot=${screenshotPath}`, `${baseUrl}?theme=${theme}#/summary`,
      ], { stdio: 'ignore' })
      process.once('error', reject)
      process.once('exit', resolve)
    })
    if (exitCode !== 0) throw new Error(`El navegador de captura terminó con código ${exitCode}`)
    return
  }
  await viewport(width, height, mobile)
  await navigate('summary', 'light')
  await evaluate(`document.querySelector('[data-action="reset"]')?.click()`)
  await sleep(120)
  if (theme === 'dark') {
    await evaluate(`document.querySelector('[data-action="theme"]')?.click()`)
    await sleep(120)
  }
  await evaluate(`scrollTo(0, 0)`)
  const shot = await send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false })
  await writeFile(join(root, 'screenshots', `${name}.png`), Buffer.from(shot.data, 'base64'))
}

await send('Page.enable')
await send('Runtime.enable')
await send('Log.enable')

try {
  await viewport(1440, 900)
  const routes = [
    ['summary', 'Mercado, contexto y decisiones'], ['radar', 'Radar de eventos'],
    ['asset/AAPL', 'AAPL · Apple Inc.'], ['signals', 'Señales explicables'],
    ['signal/sig_btc_uncertain', 'Tesis y cadena de evidencia'], ['reviews', 'Cola de revisión'],
    ['briefings', 'Briefings'], ['briefing/brf_demo_global_20260711', 'Lectura ejecutiva'],
    ['audit', 'Auditoría de ejecuciones'], ['audit/run_phase0_fixture_001', 'run_phase0_fixture_001'],
    ['assistant', 'Investiga con el contexto visible'],
  ]

  for (const [route, expectedHeading] of routes) {
    await navigate(route)
    const result = await evaluate(`({ heading: document.querySelector('h1')?.textContent.trim(), unnamed: [...document.querySelectorAll('button')].filter(button => !(button.getAttribute('aria-label') || button.textContent.trim() || button.title)).length })`)
    assert(result.heading === expectedHeading, `${route}: heading inesperado “${result.heading}”`)
    assert(result.unnamed === 0, `${route}: ${result.unnamed} botones sin nombre accesible`)
  }
  console.log('Rutas: 11/11')

  await navigate('summary')
  await evaluate(`document.querySelector('[data-action="theme"]').click()`)
  assert(await evaluate(`document.documentElement.dataset.theme`) === 'dark', 'El selector de tema no cambió a dark')
  await evaluate(`(() => { const input = document.querySelector('#search-input'); input.value = 'AAPL'; input.dispatchEvent(new Event('input', { bubbles: true })); })()`)
  assert(await evaluate(`document.querySelectorAll('#search-results [data-route]').length`) > 0, 'La búsqueda no devolvió AAPL')
  console.log('Tema y búsqueda: OK')

  await navigate('signal/sig_btc_uncertain')
  await evaluate(`document.querySelector('[data-review-status="reviewed"]').click()`)
  assert(await evaluate(`document.body.textContent.includes('Señal verificada')`), 'La revisión local no actualizó la señal')

  await navigate('briefings')
  const briefingCount = await evaluate(`document.querySelectorAll('.briefing-card').length`)
  await evaluate(`document.querySelector('[data-action="create-briefing"]').click()`)
  assert(await evaluate(`document.querySelectorAll('.briefing-card').length`) === briefingCount + 1, 'No se creó el briefing local')

  await navigate('assistant')
  const messageCount = await evaluate(`document.querySelectorAll('.chat-message').length`)
  await evaluate(`document.querySelector('[data-prompt]').click()`)
  assert(await evaluate(`document.querySelectorAll('.chat-message').length`) === messageCount + 2, 'El asistente no añadió pregunta y respuesta')
  console.log('Revisión, briefing y asistente: OK')

  await viewport(1024, 768)
  await navigate('summary')
  assert(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), 'Hay overflow horizontal a 1024 px')

  await viewport(390, 844, true)
  await navigate('summary')
  const mobileLayout = await evaluate(`({ viewport: innerWidth, body: document.documentElement.scrollWidth, mobileNav: getComputedStyle(document.querySelector('.mobile-nav')).display, assistant: getComputedStyle(document.querySelector('.assistant-rail')).display })`)
  assert(mobileLayout.viewport === 390, `Viewport móvil inesperado: ${mobileLayout.viewport}`)
  assert(mobileLayout.body <= 390, `Overflow horizontal móvil: ${mobileLayout.body}px`)
  assert(mobileLayout.mobileNav !== 'none', 'La navegación móvil no está visible')
  assert(mobileLayout.assistant === 'none', 'El rail del asistente debería ocultarse en móvil')
  console.log('Viewports 1024 y 390: OK')

  await capture('desktop-light', 1440, 900, false, 'light')
  await capture('desktop-dark', 1440, 900, false, 'dark')
  await capture('mobile-light', 390, 844, true, 'light')
  console.log('Capturas: 3/3')
  assert(browserErrors.length === 0, `Errores de navegador: ${browserErrors.join('; ')}`)

  if (failures.length) {
    console.error(`Verificación fallida (${failures.length})`)
    failures.forEach(item => console.error(`- ${item}`))
    process.exitCode = 1
  } else {
    console.log('Verificación completada: 11 vistas, interacciones clave, 3 viewports y 0 errores de navegador.')
  }
} finally {
  try { await send('Browser.close') } catch {}
  socket.close()
  browser.kill('SIGKILL')
  server.kill()
}
