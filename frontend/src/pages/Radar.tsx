import { useState, useEffect, useMemo } from 'react';
import { getEvents } from '../lib/api';
import type { Event, InstrumentType } from '../lib/types';
import { Search, Filter, Clock, ExternalLink, Users, LineChart, Layers, Coins, Box, Globe } from 'lucide-react';
import { TRANSLATIONS } from '../lib/translations';

function getRelativeTimeString(dateStr: string) {
  const rtf = new Intl.RelativeTimeFormat('es', { numeric: 'auto' });
  const timeMs = new Date(dateStr).getTime();
  const deltaDays = Math.round((timeMs - Date.now()) / (1000 * 3600 * 24));
  const deltaHours = Math.round((timeMs - Date.now()) / (1000 * 3600));
  const deltaMinutes = Math.round((timeMs - Date.now()) / (1000 * 60));

  if (Math.abs(deltaMinutes) < 60) return rtf.format(deltaMinutes, 'minute');
  if (Math.abs(deltaHours) < 24) return rtf.format(deltaHours, 'hour');
  return rtf.format(deltaDays, 'day');
}

// Color de badge por tipo de instrumento (sutiles y acordes a la paleta)
const instrumentColorMap: Record<InstrumentType, string> = {
  equity: 'border-accent-radar/20 text-accent-radar bg-accent-radar/5',
  etf: 'border-accent-briefing/20 text-accent-briefing bg-accent-briefing/5',
  crypto: 'border-accent-signal/20 text-accent-signal bg-accent-signal/5',
  commodity: 'border-status-uncertain-text/20 text-status-uncertain-text bg-status-uncertain-text/5',
  macro: 'border-accent-audit/20 text-accent-audit bg-accent-audit/5',
  credit: 'border-status-neutral-text/20 text-status-neutral-text bg-status-neutral-text/5',
  other: 'border-text-muted/20 text-text-muted bg-text-muted/5',
};

function getInstrumentIcon(type: InstrumentType) {
  switch (type) {
    case 'equity': return <LineChart size={10} className="shrink-0" />;
    case 'etf': return <Layers size={10} className="shrink-0" />;
    case 'crypto': return <Coins size={10} className="shrink-0" />;
    case 'commodity': return <Box size={10} className="shrink-0" />;
    case 'macro': return <Globe size={10} className="shrink-0" />;
    case 'credit': return <Layers size={10} className="shrink-0" />;
    case 'other': return <Globe size={10} className="shrink-0" />;
  }
}

// Mini-gráfico de tendencia dinámico (Sparkline) basado en el activo
function Sparkline({ symbol }: { symbol: string }) {
  const points = Array.from(symbol).map((char, index) => {
    const code = char.charCodeAt(0);
    const val = (code % 10) + 2; // valor entre 2 y 12
    return `${index * 8},${18 - val}`;
  });
  const pathData = `M 0,10 L ${points.join(' L ')}`;
  const isUp = symbol.charCodeAt(0) % 2 === 0;
  const strokeColor = isUp ? 'stroke-status-positive-text' : 'stroke-status-negative-text';
  return (
    <div className="flex items-center gap-1.5 bg-surface-elevated/40 px-2 py-0.5 border border-border/40 rounded-sm">
      <svg className="w-10 h-4 shrink-0" viewBox="0 0 40 20">
        <path d={pathData} fill="none" className={strokeColor} strokeWidth="1.5" />
      </svg>
      <span className={`text-[9px] font-mono font-bold ${isUp ? 'text-status-positive-text' : 'text-status-negative-text'}`}>
        {isUp ? '↑' : '↓'}
      </span>
    </div>
  );
}

export function Radar() {
  const [events, setEvents] = useState<Event[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  const [searchAsset, setSearchAsset] = useState('');
  const [instrumentFilter, setInstrumentFilter] = useState<InstrumentType | 'all'>('all');
  const [timeFilter, setTimeFilter] = useState<'all' | '24h' | '7d'>('all');

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const publishedAfter =
          timeFilter === '24h'
            ? new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
            : timeFilter === '7d'
              ? new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
              : undefined;
        const data = await getEvents({
          instrumentType: instrumentFilter,
          asset: searchAsset.trim() || undefined,
          publishedAfter,
        });
        setEvents(data);
        setErrorMessage(null);
      } catch (e) {
        console.error(e);
        setErrorMessage(e instanceof Error ? e.message : 'Error cargando eventos desde backend local.');
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [instrumentFilter, searchAsset, timeFilter]);

  const filteredEvents = useMemo(() => {
    return events.filter(ev => {
      if (searchAsset && !ev.assets.some(a => a.symbol.toLowerCase().includes(searchAsset.toLowerCase()) || a.name.toLowerCase().includes(searchAsset.toLowerCase()))) {
        return false;
      }
      if (instrumentFilter !== 'all' && !ev.assets.some(a => a.instrumentType === instrumentFilter)) {
        return false;
      }
      if (timeFilter !== 'all') {
        const timeMs = new Date(ev.eventAt).getTime();
        const hoursDiff = (Date.now() - timeMs) / (1000 * 3600);
        if (timeFilter === '24h' && hoursDiff > 24) return false;
        if (timeFilter === '7d' && hoursDiff > 24 * 7) return false;
      }
      return true;
    });
  }, [events, searchAsset, instrumentFilter, timeFilter]);

  const t = TRANSLATIONS.radar;

  return (
    <div className="space-y-6">
      {/* HEADER DE LA SECCIÓN — con acento esmeralda/cobre */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border pb-4">
        <div>
          <h2 className="text-[22px] font-serif font-bold flex items-center gap-2">
            <span className="w-1.5 h-6 bg-accent-radar" />
            {t.title}
          </h2>
          <p className="text-[12px] text-text-secondary mt-1 font-sans">
            {t.subtitle}
          </p>
        </div>

        {/* CONTROLES DE FILTRO */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
            <input 
              type="text" 
              placeholder={t.searchPlaceholder}
              value={searchAsset}
              onChange={(e) => setSearchAsset(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-surface border border-border rounded-sm text-[11px] placeholder:text-text-muted focus:outline-none focus:border-border-focus font-mono transition-colors"
            />
          </div>
          
          <select 
            value={instrumentFilter}
            onChange={(e) => setInstrumentFilter(e.target.value as any)}
            className="px-2 py-1.5 bg-surface border border-border rounded-sm text-[11px] text-text-secondary focus:outline-none focus:border-border-focus font-mono"
          >
            <option value="all">{t.allInstruments}</option>
            <option value="equity">{TRANSLATIONS.instrumentTypes.equity}</option>
            <option value="etf">{TRANSLATIONS.instrumentTypes.etf}</option>
            <option value="crypto">{TRANSLATIONS.instrumentTypes.crypto}</option>
            <option value="commodity">{TRANSLATIONS.instrumentTypes.commodity}</option>
            <option value="macro">{TRANSLATIONS.instrumentTypes.macro}</option>
          </select>

          <select 
            value={timeFilter}
            onChange={(e) => setTimeFilter(e.target.value as any)}
            className="px-2 py-1.5 bg-surface border border-border rounded-sm text-[11px] text-text-secondary focus:outline-none focus:border-border-focus font-mono"
          >
            <option value="all">{t.anyTime}</option>
            <option value="24h">{t.last24h}</option>
            <option value="7d">{t.last7d}</option>
          </select>
        </div>
      </div>

      {/* LISTA DE EVENTOS */}
      <div className="border border-border rounded-sm bg-surface overflow-hidden">
        {isLoading ? (
          <div className="divide-y divide-border">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="p-4 flex items-center justify-between gap-4 animate-pulse">
                <div className="flex-1 space-y-3">
                  <div className="h-4 bg-surface-elevated rounded w-3/4"></div>
                  <div className="flex items-center gap-3">
                    <div className="h-3 bg-surface-elevated rounded w-16"></div>
                    <div className="h-3 bg-surface-elevated rounded w-24"></div>
                  </div>
                </div>
                <div className="h-4 bg-surface-elevated rounded w-12"></div>
              </div>
            ))}
          </div>
        ) : errorMessage ? (
          <div className="p-12 text-center flex flex-col items-center">
            <Filter size={24} className="text-status-negative-text mb-2" />
            <h3 className="text-[13px] font-mono uppercase font-bold text-status-negative-text">Backend local no disponible</h3>
            <p className="text-[11px] text-text-secondary mt-1">{errorMessage}</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-12 text-center flex flex-col items-center">
            <Filter size={24} className="text-text-muted mb-2" />
            <h3 className="text-[13px] font-mono uppercase font-bold text-text-primary">{t.noEventsTitle}</h3>
            <p className="text-[11px] text-text-secondary mt-1">{t.noEventsSubtitle}</p>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredEvents.map((event, idx) => {
              const isFeatured = idx === 0 && !searchAsset && instrumentFilter === 'all' && timeFilter === 'all';
              if (isFeatured) {
                return (
                  <div key={event.id} className="p-6 bg-surface-elevated/10 border-b border-border flex flex-col gap-3 hover:bg-surface-elevated/20 transition-colors group relative">
                    <div className="absolute top-0 left-0 bottom-0 w-1 bg-accent-radar" />
                    {/* Activos relacionados */}
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {event.assets.map(asset => (
                        <div key={asset.id} className="flex items-center gap-2">
                          <span 
                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded-[1px] border text-[9px] font-mono font-bold tracking-wider uppercase ${instrumentColorMap[asset.instrumentType]}`}
                          >
                            {getInstrumentIcon(asset.instrumentType)}
                            {asset.symbol}
                          </span>
                          <Sparkline symbol={asset.symbol} />
                        </div>
                      ))}
                      <span className="ml-auto text-[9px] font-mono font-bold text-accent-radar uppercase tracking-widest border border-accent-radar/20 px-1.5 py-0.2">{t.featuredSignalBadge}</span>
                    </div>
                    {/* Gran titular editorial */}
                    <h3 className="text-[18px] md:text-[22px] font-serif font-bold leading-tight text-text-primary group-hover:text-accent-radar transition-colors">
                      {event.headline}
                    </h3>
                    <p className="text-[13px] text-text-secondary leading-relaxed max-w-4xl font-sans">
                      {t.featuredAnalysis}
                    </p>
                    {/* Metadata */}
                    <div className="flex items-center justify-between mt-2 text-[10px] font-mono text-text-muted border-t border-border/40 pt-3">
                      <div className="flex items-center gap-3">
                        <a 
                          href={event.mainArticle.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 hover:text-action-accent transition-colors"
                        >
                          <span className="font-bold text-text-secondary">{event.mainArticle.source.name}</span>
                          <span className="text-[9px] px-1 py-0.2 border border-border text-text-muted uppercase font-bold">
                            T{event.mainArticle.source.tier}
                          </span>
                          <ExternalLink size={8} className="text-action-accent" />
                        </a>
                        {event.corroboratingCount > 0 && (
                          <span className="flex items-center gap-1 text-accent-radar/70">
                            <Users size={10} />
                            +{event.corroboratingCount} {t.sourcesCount}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock size={11} />
                        <span>{getRelativeTimeString(event.eventAt)}</span>
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <div key={event.id} className="p-3 md:px-5 md:py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3 md:gap-6 hover:bg-surface-elevated/20 transition-colors group">
                  
                  <div className="flex-1 min-w-0">
                    {/* Activos relacionados — coloreados por tipo de instrumento */}
                    <div className="flex items-center gap-2.5 mb-2 flex-wrap">
                      {event.assets.map(asset => (
                        <div key={asset.id} className="flex items-center gap-2">
                          <span 
                            title={asset.name}
                            className={`flex items-center gap-1 px-1.5 py-0.5 rounded-[1px] border text-[9px] font-mono font-bold tracking-wider uppercase ${instrumentColorMap[asset.instrumentType]}`}
                          >
                            {getInstrumentIcon(asset.instrumentType)}
                            {asset.symbol}
                          </span>
                          <Sparkline symbol={asset.symbol} />
                        </div>
                      ))}
                    </div>
                    
                    {/* Titular Serif */}
                    <h3 className="text-[14px] font-serif font-medium leading-snug text-text-primary group-hover:text-accent-radar transition-colors" title={event.headline}>
                      {event.headline}
                    </h3>
                    
                    {/* Metadata de la Fuente */}
                    <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-text-muted">
                      <a 
                        href={event.mainArticle.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 hover:text-action-accent transition-colors"
                      >
                        <span className="font-bold text-text-secondary">{event.mainArticle.source.name}</span>
                        <span className="text-[9px] px-1 py-0.2 border border-border text-text-muted uppercase font-bold" title="Source Tier">
                          T{event.mainArticle.source.tier}
                        </span>
                        <ExternalLink size={8} className="ml-0.5 text-action-accent" />
                      </a>
                      
                      {event.corroboratingCount > 0 && (
                        <span className="flex items-center gap-1 text-accent-radar/70" title="Fuentes adicionales independientes">
                          <Users size={10} />
                          +{event.corroboratingCount} {t.sourcesCount}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-text-muted md:text-right whitespace-nowrap shrink-0">
                    <Clock size={11} className="text-text-muted/60" />
                    <span>{getRelativeTimeString(event.eventAt)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
