import { Search } from 'lucide-react'
import { useDeferredValue, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useInstrumentsQuery, useMarketQuotesQuery } from '../../shared/api/queries'
import { formatCurrency, formatPercent } from '../../shared/lib/format'
import { DataModeBadge } from '../../shared/ui/badges'
import { EmptyState, ErrorState, LoadingSkeleton, RefreshButton } from '../../shared/ui/primitives'

export function MarketsPage() {
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query.trim())
  const instrumentsQuery = useInstrumentsQuery(deferredQuery)
  const instruments = useMemo(() => instrumentsQuery.data?.items ?? [], [instrumentsQuery.data?.items])
  const symbols = instruments.map(item => item.symbol)
  const firstQuotes = useMarketQuotesQuery(symbols.slice(0, 10))
  const secondQuotes = useMarketQuotesQuery(symbols.slice(10, 20))
  const thirdQuotes = useMarketQuotesQuery(symbols.slice(20, 25))
  const quotes = useMemo(
    () => [...(firstQuotes.data?.items ?? []), ...(secondQuotes.data?.items ?? []), ...(thirdQuotes.data?.items ?? [])],
    [firstQuotes.data?.items, secondQuotes.data?.items, thirdQuotes.data?.items],
  )
  const quoteBySymbol = useMemo(() => new Map(quotes.map(item => [item.symbol, item])), [quotes])
  const isLoading = instrumentsQuery.isLoading || firstQuotes.isLoading

  if (isLoading) return <LoadingSkeleton rows={12} />
  if (instrumentsQuery.isError) {
    return (
      <ErrorState
        title="No se pudo cargar el universo"
        description="La API no devolvió el catálogo productivo."
        action={<RefreshButton label="Reintentar" busy={instrumentsQuery.isFetching} onClick={() => void instrumentsQuery.refetch()} />}
      />
    )
  }

  return (
    <div className="page-stack markets-page">
      <header className="page-heading">
        <div>
          <p className="section-eyebrow">Mercado productivo</p>
          <h1>25 instrumentos, no cuatro ejemplos</h1>
          <p>Empresas, benchmarks, cripto y energía consultados exclusivamente por el backend.</p>
        </div>
      </header>

      <label className="instrument-search">
        <Search size={17} aria-hidden="true" />
        <input
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Buscar símbolo o empresa"
          aria-label="Buscar instrumento"
        />
        <span>{instruments.length} resultados</span>
      </label>

      {deferredQuery.length === 1 ? (
        <EmptyState title="Escribe al menos dos caracteres" description="La búsqueda está limitada para proteger las cuotas de proveedores." />
      ) : instruments.length ? (
        <section className="instrument-grid" aria-label="Universo de instrumentos">
          {instruments.map(instrument => {
            const quote = quoteBySymbol.get(instrument.symbol)
            return (
              <Link className="instrument-card" key={instrument.id} to={`/assets/${instrument.symbol}`}>
                <div className="instrument-card__head">
                  <div>
                    <span className="section-eyebrow">{instrument.instrumentType}</span>
                    <h2>{instrument.symbol}</h2>
                  </div>
                  {quote ? <DataModeBadge mode={quote.dataMode} /> : null}
                </div>
                <p>{instrument.name}</p>
                <strong>{formatCurrency(quote?.price ?? null, instrument.currency)}</strong>
                <span className={quote?.changePercent == null ? 'market-change' : quote.changePercent >= 0 ? 'market-change market-change--up' : 'market-change market-change--down'}>
                  {quote?.changePercent == null ? 'Cambio no disponible' : formatPercent(quote.changePercent)}
                </span>
                <small>{quote?.provider ?? instrument.exchange}</small>
              </Link>
            )
          })}
        </section>
      ) : (
        <EmptyState title="Sin coincidencias" description="Prueba con el símbolo o nombre de otra empresa del universo productivo." />
      )}
    </div>
  )
}
