const RECENT_RUNS_KEY = 'nexomercado:recent-runs'
const RECENT_BRIEFINGS_KEY = 'nexomercado:recent-briefings'

function safeParse(value: string | null): string[] {
  if (!value) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string') : []
  } catch {
    return []
  }
}

function pushId(key: string, id: string): void {
  if (typeof window === 'undefined') return
  const next = [id, ...safeParse(window.localStorage.getItem(key)).filter(item => item !== id)].slice(0, 10)
  window.localStorage.setItem(key, JSON.stringify(next))
}

function readIds(key: string): string[] {
  if (typeof window === 'undefined') return []
  return safeParse(window.localStorage.getItem(key))
}

export const recentRunsStorage = {
  push: (id: string) => pushId(RECENT_RUNS_KEY, id),
  read: () => readIds(RECENT_RUNS_KEY),
}

export const recentBriefingsStorage = {
  push: (id: string) => pushId(RECENT_BRIEFINGS_KEY, id),
  read: () => readIds(RECENT_BRIEFINGS_KEY),
}
