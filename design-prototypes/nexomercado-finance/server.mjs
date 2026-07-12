import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('.', import.meta.url))
const port = Number(process.env.PORT || 4175)
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.md': 'text/markdown; charset=utf-8', '.png': 'image/png' }

createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, `http://${request.headers.host}`).pathname)
    const safePath = normalize(pathname).replace(/^(\.\.[/\\])+/, '')
    let target = join(root, safePath === '/' ? 'index.html' : safePath)
    if ((await stat(target)).isDirectory()) target = join(target, 'index.html')
    const body = await readFile(target)
    response.writeHead(200, { 'Content-Type': types[extname(target)] || 'application/octet-stream', 'Cache-Control': 'no-store' })
    response.end(body)
  } catch {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' })
    response.end('No encontrado')
  }
}).listen(port, '127.0.0.1', () => {
  console.log(`NexoMercado Finance disponible en http://127.0.0.1:${port}`)
})

