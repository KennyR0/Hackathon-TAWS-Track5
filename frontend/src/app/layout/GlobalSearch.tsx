import { Search } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEventsQuery, useSignalsQuery } from '../../shared/api/queries'

interface SearchResult {
  key: string
  kind: string
  label: string
  detail: string
  to: string
}

export function GlobalSearch() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const eventsQuery = useEventsQuery()
  const signalsQuery = useSignalsQuery()

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return []

    const signals: SearchResult[] = (signalsQuery.data?.items ?? []).flatMap(signal => {
      const text = `${signal.asset.symbol} ${signal.asset.name} ${signal.thesis ?? ''}`.toLowerCase()
      if (!text.includes(normalized)) return []
      return [{ key: `signal-${signal.id}`, kind: 'Señal', label: signal.asset.symbol, detail: signal.thesis ?? signal.asset.name, to: `/signals/${signal.id}` }]
    })
    const events: SearchResult[] = (eventsQuery.data?.items ?? []).flatMap(event => {
      const text = `${event.title} ${event.summary} ${event.relatedAssets.map(asset => asset.symbol).join(' ')}`.toLowerCase()
      if (!text.includes(normalized)) return []
      return [{ key: `event-${event.id}`, kind: 'Evento', label: event.title, detail: event.relatedAssets.map(asset => asset.symbol).join(', '), to: `/radar?event=${event.id}` }]
    })

    return [...signals, ...events].slice(0, 7)
  }, [eventsQuery.data?.items, query, signalsQuery.data?.items])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        inputRef.current?.focus()
        setOpen(true)
      }
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const goTo = (result: SearchResult) => {
    navigate(result.to)
    setQuery('')
    setOpen(false)
  }

  return (
    <div className="global-search">
      <Search size={16} aria-hidden="true" />
      <input
        ref={inputRef}
        value={query}
        aria-label="Buscar activo, señal o evento"
        placeholder="Buscar activo, señal o evento"
        onFocus={() => setOpen(true)}
        onChange={event => {
          setQuery(event.target.value)
          setOpen(true)
        }}
        onKeyDown={event => {
          if (event.key === 'Enter' && results[0]) goTo(results[0])
        }}
      />
      <kbd>⌘ K</kbd>
      {open && query.trim() ? (
        <div className="search-results" role="listbox" aria-label="Resultados de búsqueda">
          {results.length ? results.map(result => (
            <button key={result.key} type="button" role="option" aria-selected="false" onClick={() => goTo(result)}>
              <span>{result.kind}</span>
              <strong>{result.label}</strong>
              <small>{result.detail}</small>
            </button>
          )) : <p>Sin coincidencias en los datos disponibles.</p>}
        </div>
      ) : null}
    </div>
  )
}
