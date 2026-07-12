import { useState, useEffect, useMemo } from 'react';
import { createDraftBriefing } from '../lib/api';
import type { Briefing } from '../lib/types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Share, AlertTriangle, FileText, CheckCircle, Clock, TrendingUp, TrendingDown, Minus, Check, X, AlertCircle as AlertCircleIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { TRANSLATIONS } from '../lib/translations';

export function Briefing() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const data = await createDraftBriefing();
        setBriefing(data);
        setErrorMessage(null);
      } catch (e) {
        console.error(e);
        setErrorMessage(e instanceof Error ? e.message : 'Error creando briefing desde backend local.');
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const stats = useMemo(() => {
    if (!briefing) return { positive: 0, negative: 0, uncertain: 0, pending: 0 };
    let positive = 0, negative = 0, uncertain = 0, pending = 0;
    briefing.signals.forEach(sig => {
      if (sig.impact === 'positive') positive++;
      else if (sig.impact === 'negative') negative++;
      else uncertain++;
      
      if (sig.reviewStatus === 'pending_review') pending++;
    });
    return { positive, negative, uncertain, pending };
  }, [briefing]);

  const inconsistentSignals = useMemo(() => {
    if (!briefing || briefing.status !== 'shareable') return [];
    return briefing.signals.filter(
      sig => sig.reviewStatus === 'discarded' || sig.status === 'insufficient_evidence'
    );
  }, [briefing]);

  const allResearchActions = useMemo(() => {
    if (!briefing) return [];
    const actions = new Set<string>();
    briefing.signals.forEach(sig => {
      sig.suggestedResearchActions.forEach(action => actions.add(action));
    });
    return Array.from(actions);
  }, [briefing]);

  const t = TRANSLATIONS.briefing;

  if (isLoading) {
    return <div className="p-8 text-center text-[13px] text-accent-briefing animate-pulse">{t.loading}</div>;
  }

  if (!briefing) {
    return <div className="p-8 text-center text-[13px] text-status-negative-text">{errorMessage ?? t.errorLoading}</div>;
  }

  const isDraft = briefing.status === 'draft';
  const hasInconsistencies = inconsistentSignals.length > 0;

  return (
    <div className={`space-y-6 max-w-4xl mx-auto pb-12 ${isDraft ? 'opacity-90' : ''}`}>
      
      {/* HEADER DEL BRIEFING — Estilo Recorte de Periódico Físico */}
      <div className={`p-6 border relative overflow-hidden flex flex-col md:flex-row gap-6 items-start ${
        isDraft ? 'bg-surface border-dashed border-text-muted/40' : 'bg-surface border-border border-l-4 border-l-accent-briefing'
      }`}>
        <div className="absolute top-0 right-0 w-24 h-24 bg-accent-briefing/5 rounded-bl-full pointer-events-none" />
        
        {isDraft && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -rotate-12 text-[100px] font-bold text-border/30 pointer-events-none select-none tracking-widest z-0 font-mono">
            DRAFT
          </div>
        )}

        <div className="flex-1 relative z-10 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`text-[9px] font-mono font-bold uppercase tracking-wider px-1.5 py-0.2 border border-current rounded-sm ${isDraft ? 'text-status-uncertain-text' : 'text-status-positive-text'}`}>
              {isDraft ? t.draftBadge : t.executiveBadge}
            </span>
            <span className="text-[10px] text-text-muted font-mono flex items-center gap-1">
              <Clock size={10} />
              {new Intl.DateTimeFormat('es', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(briefing.generatedAt))}
            </span>
          </div>

          <h2 className="text-[26px] font-serif font-bold text-text-primary leading-tight">
            {briefing.title}
          </h2>
          <p className="text-[15px] font-serif italic text-text-secondary leading-relaxed max-w-2xl border-l border-border/60 pl-4 py-1 bg-surface-elevated/10">
            {briefing.summary}
          </p>
        </div>

        {/* Bloque Asimétrico Lateral de Highlights */}
        <div className="w-full md:w-56 shrink-0 border border-border/80 bg-surface-elevated/20 p-4 rounded-sm font-mono text-[10px] text-text-secondary space-y-3 relative z-10 self-stretch flex flex-col justify-between">
          <div>
            <div className="font-bold uppercase tracking-wider text-text-primary mb-2 border-b border-border/40 pb-1 flex items-center gap-1.5">
              <FileText size={10} className="text-accent-briefing" /> {t.quickStats}
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <span>{t.totalSignals}</span>
                <span className="font-bold text-text-primary">{briefing.signals.length}</span>
              </div>
              <div className="flex justify-between">
                <span>{t.inconsistencies}</span>
                <span className={`font-bold ${hasInconsistencies ? 'text-status-negative-text' : 'text-status-positive-text'}`}>
                  {inconsistentSignals.length}
                </span>
              </div>
            </div>
          </div>
          
          <div className="pt-3 border-t border-border/40 text-[9px] text-text-muted">
            NEXOMERCADO AI INTELLIGENCE UNIT
          </div>
        </div>
      </div>

      {/* Tablero Resumen de Señales */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-surface border border-border p-3.5 rounded-sm flex flex-col justify-between h-20">
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{t.positiveSignalsCount}</span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-2xl font-mono font-bold text-status-positive-text">{stats.positive}</span>
            <span className="text-status-positive-text text-[10px] font-mono flex items-center gap-0.5 font-bold uppercase">
              <TrendingUp size={10} /> {t.activeBadge}
            </span>
          </div>
        </div>
        <div className="bg-surface border border-border p-3.5 rounded-sm flex flex-col justify-between h-20">
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{t.negativeSignalsCount}</span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-2xl font-mono font-bold text-status-negative-text">{stats.negative}</span>
            <span className="text-status-negative-text text-[10px] font-mono flex items-center gap-0.5 font-bold uppercase">
              <TrendingDown size={10} /> {t.riskBadge}
            </span>
          </div>
        </div>
        <div className="bg-surface border border-border p-3.5 rounded-sm flex flex-col justify-between h-20">
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{t.uncertainSignalsCount}</span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-2xl font-mono font-bold text-status-uncertain-text">{stats.uncertain}</span>
            <span className="text-status-uncertain-text text-[10px] font-mono flex items-center gap-0.5 font-bold uppercase">
              <Minus size={10} /> {t.alertBadge}
            </span>
          </div>
        </div>
        <div className="bg-surface border border-border p-3.5 rounded-sm flex flex-col justify-between h-20 border-t border-t-accent-signal">
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{t.pendingReviewCount}</span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-2xl font-mono font-bold text-accent-signal">{stats.pending}</span>
            <span className="text-accent-signal text-[10px] font-mono flex items-center gap-0.5 font-bold uppercase">
              <AlertTriangle size={10} /> {t.pendingBadge}
            </span>
          </div>
        </div>
      </div>

      {/* VALIDACIÓN DE INCONSISTENCIA */}
      {hasInconsistencies && (
        <div className="bg-status-negative-bg/10 border border-status-negative-text/30 p-4 rounded-sm flex items-start gap-3">
          <AlertTriangle size={15} className="text-status-negative-text shrink-0 mt-0.5" />
          <div>
            <h4 className="text-[11px] font-mono font-bold text-status-negative-text uppercase tracking-wider">{t.inconsistencyAlertTitle}</h4>
            <p className="text-[12px] text-status-negative-text/90 mt-1 leading-relaxed">
              {t.inconsistencyAlertText}
            </p>
          </div>
        </div>
      )}

      {/* SEÑALES INCLUIDAS */}
      <div>
        <h3 className="text-[11px] font-mono font-bold uppercase tracking-wider border-b border-border pb-2 mb-4 flex items-center gap-2">
          {t.watchlistSignalsTitle} <span className="text-accent-briefing font-bold">({briefing.signals.length})</span>
        </h3>
        
        <div className="space-y-3">
          {briefing.signals.map(signal => {
            const isInvalid = signal.reviewStatus === 'discarded' || signal.status === 'insufficient_evidence';
            return (
              <div key={signal.id} className={`p-4 border rounded-sm flex flex-col md:flex-row md:items-center gap-4 transition-colors ${isInvalid ? 'bg-status-negative-bg/5 border-status-negative-text/20' : 'bg-surface border-border hover:border-accent-briefing/20'}`}>
                
                {/* Ticker y Status */}
                <div className="w-36 shrink-0 flex items-center gap-3 md:block">
                  <div className="text-[18px] font-mono font-bold text-text-primary tracking-tight">{signal.asset.symbol}</div>
                  <div className="mt-1 flex flex-col gap-1 items-start">
                    <div className="flex items-center gap-1">
                      {signal.reviewStatus === 'reviewed' && <Check size={10} className="text-status-positive-text" />}
                      {signal.reviewStatus === 'discarded' && <X size={10} className="text-status-negative-text" />}
                      {signal.reviewStatus === 'pending_review' && <AlertCircleIcon size={10} className="text-status-uncertain-text" />}
                      <StatusBadge 
                        type={signal.reviewStatus === 'reviewed' ? 'reviewed' : signal.reviewStatus === 'discarded' ? 'discarded' : 'pending_review'} 
                      />
                    </div>
                  </div>
                </div>

                {/* Resumen corto e Impacto */}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">{t.impactLabel}</span>
                    <div className="flex items-center gap-1">
                      {signal.impact === 'positive' && <TrendingUp size={11} className="text-status-positive-text" />}
                      {signal.impact === 'negative' && <TrendingDown size={11} className="text-status-negative-text" />}
                      {signal.impact === 'neutral' && <Minus size={11} className="text-status-neutral-text" />}
                      <StatusBadge type={signal.impact as any} />
                    </div>
                  </div>
                  <p className="text-[13px] text-text-secondary leading-relaxed line-clamp-2">
                    {signal.claims[0]?.description || 'Pendiente de extracción de claims para esta señal específica. Requiere validación de fuentes subyacentes.'}
                  </p>
                </div>

                {/* Acción */}
                <div className="shrink-0 md:text-right mt-2 md:mt-0">
                  <Link to="/signal" className="text-[11px] font-mono font-bold text-accent-briefing hover:text-action-hover uppercase tracking-wider border border-accent-briefing/20 hover:border-action-hover px-2.5 py-1 transition-colors">
                    {t.viewDetailButton}
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ACCIONES DE INVESTIGACIÓN AGREGADAS */}
      {allResearchActions.length > 0 && (
        <div className="bg-surface border border-border rounded-sm overflow-hidden mt-8">
          <div className="bg-surface-elevated px-4 py-2.5 border-b border-border flex items-center gap-2">
            <CheckCircle size={14} className="text-accent-briefing" />
            <h3 className="text-[11px] font-mono font-bold text-text-primary uppercase tracking-wider">{t.suggestedResearchTitle}</h3>
          </div>
          <ul className="p-4 space-y-2">
            {allResearchActions.map((action, idx) => (
              <li key={idx} className="flex items-start gap-2.5 text-[13px] text-text-secondary leading-relaxed">
                <span className="text-accent-briefing font-mono font-bold mt-0.5">{idx + 1}.</span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* EXTENSIÓN: COMPARTIR (Habilitado para mock) */}
      <div className="pt-8 flex justify-end">
        <button 
          onClick={() => {
            if (!isDraft && !hasInconsistencies) {
              alert("Briefing compartido con éxito (Simulado)");
            }
          }}
          disabled={isDraft || hasInconsistencies}
          className={`flex items-center gap-2 px-4 py-2 border rounded-sm text-[12px] font-mono font-bold uppercase transition-all ${
            isDraft || hasInconsistencies 
              ? 'border-border text-text-muted cursor-not-allowed bg-surface' 
              : 'border-accent-briefing text-accent-briefing hover:bg-accent-briefing hover:text-bg cursor-pointer'
          }`}
          title={isDraft ? t.draftTooltip : hasInconsistencies ? t.inconsistencyTooltip : t.exportTooltip}
        >
          <Share size={14} />
          <span>{t.exportButton}</span>
        </button>
      </div>
    </div>
  );
}
