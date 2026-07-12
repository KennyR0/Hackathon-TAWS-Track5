import { useState, useEffect } from 'react';
import { demoIds, getSignal, saveSignalReview } from '../lib/api';
import type { Signal, Claim, Evidence, AnalysisStatus, ReviewStatus } from '../lib/types';
import { StatusBadge } from '../components/ui/StatusBadge';
import { AlertTriangle, TrendingUp, Info, Link as LinkIcon, Database, CheckCircle2, XCircle } from 'lucide-react';
import { TRANSLATIONS } from '../lib/translations';

function formatDateTime(dateStr: string) {
  return new Intl.DateTimeFormat('es', { 
    dateStyle: 'short', timeStyle: 'short' 
  }).format(new Date(dateStr));
}

function renderStatusBadge(status: AnalysisStatus) {
  switch (status) {
    case 'completed': return <StatusBadge type="positive" label={TRANSLATIONS.statuses.completed} />;
    case 'processing': return <StatusBadge type="uncertain" label={TRANSLATIONS.statuses.processing} />;
    case 'insufficient_evidence': return <StatusBadge type="negative" label={TRANSLATIONS.statuses.insufficient_evidence} />;
    case 'failed': return <StatusBadge type="negative" label={TRANSLATIONS.statuses.failed} />;
  }
}

// Componente para la trazabilidad (Claim -> Evidence -> Source)
function ClaimCard({ claim, evidence, variant }: { claim: Claim, evidence?: Evidence, variant: 'favorable' | 'counter' }) {
  if (!evidence) return null;
  const borderColor = variant === 'favorable' ? 'border-l-status-positive-text' : 'border-l-status-negative-text';
  const t = TRANSLATIONS.signalDetail;
  return (
    <div className={`bg-surface border border-border border-l-2 ${borderColor} rounded-sm p-3 mb-3 text-[13px]`}>
      <p className="font-sans text-text-primary mb-2.5 leading-relaxed">{claim.description}</p>
      
      <details className="group [&_summary::-webkit-details-marker]:hidden">
        <summary className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-text-muted uppercase tracking-wider cursor-pointer select-none hover:text-action-accent transition-colors">
          <span className="group-open:rotate-90 transition-transform text-action-accent">▶</span>
          {t.viewEvidenceSource}
        </summary>
        <div className="mt-3 pl-3 border-l border-border space-y-2">
          <p className="text-[12px] text-text-secondary italic">"{evidence.text}"</p>
          <div className="flex flex-wrap items-center gap-3 text-[10px] text-text-muted font-mono">
            <span className="flex items-center gap-1" title="Fuente">
              <Database size={10} className="text-accent-signal" />
              {evidence.sourceName} <span className="uppercase text-[9px] px-1 py-0.2 border border-border rounded-sm">{t.sourceTier} {evidence.sourceTier}</span>
            </span>
            <span className="flex items-center gap-1">
              <LinkIcon size={10} className="text-action-accent" />
              {evidence.articleTitle}
            </span>
            <span className="border border-border px-1 py-0.2 text-accent-audit" title={t.cryptographicHash}>
              #{evidence.hash}
            </span>
          </div>
        </div>
      </details>
    </div>
  );
}

interface HumanReviewPanelProps {
  signal: Signal;
  onSave: (newStatus: Exclude<ReviewStatus, 'pending_review'>, justification: string) => Promise<void>;
}

function HumanReviewPanel({ signal, onSave }: HumanReviewPanelProps) {
  const [selectedStatus, setSelectedStatus] = useState(signal.reviewStatus);
  const [justification, setJustification] = useState('');
  const [saveLogs, setSaveLogs] = useState<{ status: string; justification: string; savedAt: string }[]>([]);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const t = TRANSLATIONS.signalDetail;

  const handleSave = async () => {
    if (selectedStatus === 'pending_review') return;
    setIsSaving(true);
    setErrorMessage(null);
    try {
      await onSave(selectedStatus, justification);
      setSaveLogs(prev => [
        { status: selectedStatus, justification, savedAt: new Date().toISOString() },
        ...prev
      ]);
      setIsSuccess(true);
      setJustification('');
      setTimeout(() => setIsSuccess(false), 3000);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'No se pudo guardar la revision.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-surface border border-border p-5 rounded-sm space-y-4">
      <div>
        <h3 className="text-[12px] font-mono font-bold text-accent-signal uppercase tracking-wider flex items-center gap-1.5">
          <Database size={12} className="text-accent-signal" /> {t.humanReviewCenter}
        </h3>
        {/* Tu validación / Decisión del analista */}
        <h4 className="text-[13px] font-serif font-bold text-text-primary mt-1.5">{t.analystDecision}</h4>
        <p className="text-[11px] text-text-secondary mt-0.5 font-sans">
          {t.analystDecisionSubtitle}
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Selector de Estado */}
        <div className="space-y-2">
          <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block">{t.reviewStatusLabel}</label>
          <div className="flex gap-2">
            {(['reviewed', 'escalated', 'discarded'] as const).map(status => {
              const isActive = selectedStatus === status;
              let activeStyle = '';
              if (isActive) {
                activeStyle = status === 'reviewed' ? 'border-status-positive-text bg-status-positive-bg text-status-positive-text font-bold' :
                              status === 'escalated' ? 'border-accent-signal bg-accent-signal/15 text-accent-signal font-bold' :
                              'border-status-negative-text bg-status-negative-bg text-status-negative-text font-bold';
              } else {
                activeStyle = 'border-border bg-bg text-text-secondary hover:border-border-focus';
              }
              return (
                <button
                  key={status}
                  type="button"
                  onClick={() => setSelectedStatus(status)}
                  className={`flex-1 px-2.5 py-1.5 border rounded-sm text-[11px] font-mono uppercase tracking-wider transition-colors ${activeStyle}`}
                >
                  {status === 'reviewed' ? t.approveAction : status === 'escalated' ? t.escalateAction : t.discardAction}
                </button>
              );
            })}
          </div>
        </div>

        {/* Input de Justificación */}
        <div className="space-y-2">
          <label className="text-[10px] font-mono text-text-muted uppercase tracking-wider block">{t.justificationLabel}</label>
          <textarea
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder={t.justificationPlaceholder}
            className="w-full h-12 px-3 py-1.5 bg-bg border border-border rounded-sm text-[12px] font-sans placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors resize-none"
          />
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-border/40 pt-4 mt-2">
        <div className="text-[10px] font-mono text-text-muted uppercase">
          {isSuccess && (
            <span className="text-status-positive-text font-bold animate-pulse">
              {t.saveMockSuccess}
            </span>
          )}
          {errorMessage && (
            <span className="text-status-negative-text font-bold">
              {errorMessage}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={!justification.trim() || isSaving}
          className={`px-4 py-2 border rounded-sm text-[11px] font-mono font-bold uppercase transition-all ${
            justification.trim() && !isSaving
              ? 'border-accent-signal text-accent-signal hover:bg-accent-signal hover:text-bg cursor-pointer'
              : 'border-border text-text-muted cursor-not-allowed bg-surface'
          }`}
        >
          {isSaving ? 'Guardando...' : t.confirmButton}
        </button>
      </div>

      {/* Historial de revisiones en esta sesión */}
      {saveLogs.length > 0 && (
        <div className="border-t border-border/40 pt-4 space-y-2">
          <h4 className="text-[9px] font-mono font-bold text-text-muted uppercase tracking-wider">{t.sessionHistory}</h4>
          <div className="space-y-1.5">
            {saveLogs.map((log, idx) => (
              <div key={idx} className="flex justify-between items-start gap-4 text-[10px] font-mono border-b border-border/10 pb-1.5 last:border-0">
                <div className="flex items-center gap-2">
                  <span className={`px-1 py-0.2 border rounded-[1px] uppercase font-bold text-[9px] ${
                    log.status === 'reviewed' ? 'border-status-positive-text/30 text-status-positive-text bg-status-positive-bg/10' :
                    log.status === 'escalated' ? 'border-accent-signal/30 text-accent-signal bg-accent-signal/5' :
                    'border-status-negative-text/30 text-status-negative-text bg-status-negative-bg/10'
                  }`}>
                    {log.status === 'reviewed' ? t.approveAction : log.status === 'escalated' ? t.escalateAction : t.discardAction}
                  </span>
                  <span className="text-text-secondary">"{log.justification}"</span>
                </div>
                <span className="text-text-muted text-[8px] whitespace-nowrap">
                  {new Intl.DateTimeFormat('es', { timeStyle: 'medium' }).format(new Date(log.savedAt))}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function SignalDetail() {
  const [signal, setSignal] = useState<Signal | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const data = await getSignal(demoIds.signalId);
        setSignal(data);
        setErrorMessage(null);
      } catch (e) {
        console.error(e);
        setErrorMessage(e instanceof Error ? e.message : 'Error cargando señal desde backend local.');
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  if (isLoading) {
    return <div className="p-8 font-mono text-[12px] text-accent-signal animate-pulse">{TRANSLATIONS.signalDetail.loading}</div>;
  }

  if (!signal) {
    return <div className="p-8 text-center text-[13px] text-status-negative-text font-mono">{errorMessage ?? TRANSLATIONS.signalDetail.errorLoading}</div>;
  }

  const isCompleted = signal.status === 'completed';
  const snapshot = signal.marketSnapshot;
  const t = TRANSLATIONS.signalDetail;

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      
      {/* 1. DISCLAIMER PERMANENTE */}
      <div className="bg-status-uncertain-bg/10 border border-status-uncertain-text/20 text-status-uncertain-text px-4 py-3 rounded-sm flex items-start gap-3">
        <AlertTriangle size={15} className="mt-0.5 shrink-0" />
        <div className="text-[12px] leading-relaxed">
          <strong className="font-mono text-[11px] uppercase tracking-wider mr-1">{t.disclaimerTitle}</strong> 
          {t.disclaimerText}
        </div>
      </div>

      {/* 2.5 HUMAN REVIEW CONTROL CENTER */}
      <HumanReviewPanel 
        signal={signal} 
        onSave={async (newStatus, justification) => {
          const result = await saveSignalReview(signal.id, newStatus, justification);
          setSignal(result.signal);
        }} 
      />

      {/* 2. ENCABEZADO Y CONFIANZA — acento ámbar */}
      <header className="flex flex-col md:flex-row md:items-start justify-between gap-6 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-3 mb-2 flex-wrap">
            <span className="w-1.5 h-8 bg-accent-signal" />
            <h1 className="text-3xl font-mono font-bold tracking-tight text-text-primary">{signal.asset.symbol}</h1>
            <span className="text-[15px] text-text-secondary font-medium font-sans">{signal.asset.name}</span>
            {renderStatusBadge(signal.status)}
          </div>
          
          <div className="flex items-center gap-2 mt-3 ml-3">
            <span className="text-[10px] text-text-muted uppercase font-mono tracking-wider">{t.estimatedImpact}</span>
            <StatusBadge type={signal.impact === 'positive' ? 'positive' : signal.impact === 'negative' ? 'negative' : 'neutral'} label={TRANSLATIONS.impacts[signal.impact]} />
          </div>
        </div>

        {/* Nivel de Confianza — Segmented Technical Gauge */}
        {signal.status !== 'insufficient_evidence' && signal.status !== 'failed' && (
          <div className="bg-surface border border-border rounded-sm p-4 min-w-[240px] flex flex-col justify-between">
            <div className="flex justify-between items-end mb-3">
              <span className="text-[10px] text-text-muted uppercase font-mono tracking-wider">{t.confidence}</span>
              <span className="text-xl font-mono font-bold text-accent-signal">{(signal.confidenceScore * 100).toFixed(1)}%</span>
            </div>
            
            {/* Segmented meter blocks */}
            <div className="flex gap-1 h-2">
              {Array.from({ length: 10 }).map((_, idx) => {
                const threshold = (idx + 1) / 10;
                const active = signal.confidenceScore >= threshold;
                let activeColor = 'bg-surface-elevated';
                if (active) {
                  activeColor = signal.confidenceScore > 0.7 ? 'bg-status-positive-text' : 
                                signal.confidenceScore > 0.4 ? 'bg-accent-signal' : 'bg-status-negative-text';
                }
                return (
                  <div 
                    key={idx} 
                    className={`flex-1 h-full rounded-sm border border-border/10 transition-all ${activeColor}`} 
                    title={`${threshold * 100}%`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-[8px] font-mono text-text-muted mt-2 uppercase tracking-widest">
              <span>{t.confidenceLow}</span>
              <span>{t.confidenceMid}</span>
              <span>{t.confidenceHigh}</span>
            </div>
          </div>
        )}
      </header>

      {/* 3. CONTEXTO DE MERCADO (MARKET SNAPSHOT) */}
      <section className="bg-surface border border-border rounded-sm p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-[11px] font-mono font-bold text-accent-signal uppercase tracking-wider flex items-center gap-2">
            <TrendingUp size={12} /> {t.marketSnapshot}
          </h2>
          <span className={`text-[10px] font-mono font-bold uppercase border border-current rounded-sm px-2 py-0.5 ${
            signal.dataMode === 'live' ? 'text-status-positive-text' :
            signal.dataMode === 'fallback' ? 'text-status-negative-text' :
            'text-status-uncertain-text'
          }`}>
            {TRANSLATIONS.runtime.dataMode}: {TRANSLATIONS.dataModes[signal.dataMode]}
          </span>
        </div>
        {signal.warnings.length > 0 && (
          <div className="mb-4 border border-status-uncertain-text/25 bg-status-uncertain-bg/10 rounded-sm px-3 py-2 text-[11px] text-status-uncertain-text font-mono">
            <div className="font-bold uppercase mb-1">{TRANSLATIONS.runtime.warnings}</div>
            {signal.warnings.map(warning => (
              <div key={warning}>- {warning}</div>
            ))}
          </div>
        )}
        
        <div className="flex flex-col md:flex-row gap-8 items-start md:items-center">
          {/* Cifra protagonista */}
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-[14px] text-text-secondary font-mono uppercase">{snapshot.currency}</span>
              <span className="text-3xl font-mono font-bold tracking-tight text-text-primary tabular-nums">{snapshot.price.toFixed(2)}</span>
            </div>
            <div className={`inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded-sm text-[12px] font-mono font-bold border ${
              snapshot.change24h >= 0 
                ? 'bg-status-positive-bg/40 border-status-positive-text/20 text-status-positive-text' 
                : 'bg-status-negative-bg/40 border-status-negative-text/20 text-status-negative-text'
            }`}>
              {snapshot.change24h >= 0 ? '↑' : '↓'}
              {snapshot.change24h > 0 ? '+' : ''}{snapshot.change24h.toFixed(2)}% (24h)
            </div>
          </div>

          {/* Gráfico Simple (Barra Comparativa vs Benchmark) */}
          {snapshot.benchmarkSymbol && snapshot.benchmarkChange24h !== undefined && (
            <div className="flex-1 w-full max-w-sm">
              <div className="text-[10px] font-mono text-text-secondary mb-2 flex justify-between uppercase">
                <span>{t.vsBenchmark} ({snapshot.benchmarkSymbol})</span>
                <span className="tabular-nums font-bold">{snapshot.benchmarkChange24h > 0 ? '+' : ''}{snapshot.benchmarkChange24h}%</span>
              </div>
              <div className="relative h-6 w-full bg-surface-elevated border border-border rounded-sm overflow-hidden flex items-center">
                <div className="absolute top-0 bottom-0 left-1/2 w-px bg-text-muted/30 z-10" />
                {/* Barra de Asset */}
                <div 
                  className={`absolute h-4 z-0 rounded-sm ${snapshot.change24h >= 0 ? 'bg-status-positive-text/30 right-1/2 origin-right scale-x-[-1]' : 'bg-status-negative-text/30 left-1/2'} transition-all`}
                  style={{ width: `${Math.min(Math.abs(snapshot.change24h) * 10, 50)}%` }}
                />
                {/* Barra de Benchmark */}
                <div 
                  className={`absolute h-1.5 z-20 rounded-sm ${snapshot.benchmarkChange24h >= 0 ? 'bg-text-muted/50 right-1/2 origin-right scale-x-[-1]' : 'bg-text-muted/50 left-1/2'}`}
                  style={{ width: `${Math.min(Math.abs(snapshot.benchmarkChange24h) * 10, 50)}%` }}
                />
              </div>
              <div className="flex justify-between text-[9px] text-text-muted mt-1 font-mono uppercase tracking-wider">
                <span>{t.underperform}</span>
                <span>{t.outperform}</span>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="md:ml-auto text-right text-[10px] text-text-muted font-mono space-y-1">
            <div>{t.dataAsOf} {formatDateTime(snapshot.dataAsOf)}</div>
            <div>{t.retrievedAt} {formatDateTime(snapshot.retrievedAt)}</div>
          </div>
        </div>
      </section>

      {/* 4. EVIDENCIA: DOS COLUMNAS ASIMÉTRICAS */}
      {isCompleted && (
        <section className="grid grid-cols-1 md:grid-cols-5 gap-6">
          {/* Favorable — Columna Principal */}
          <div className="md:col-span-3">
            <h3 className="text-[12px] font-mono font-bold text-status-positive-text uppercase tracking-wider flex items-center gap-2 mb-4 border-b border-status-positive-text/20 pb-2">
              <CheckCircle2 size={14} />
              {t.favorableEvidence}
            </h3>
            {signal.claims
              .filter(c => signal.favorableEvidenceIds.includes(c.evidenceId))
              .map(claim => (
                <ClaimCard 
                  key={claim.id} 
                  claim={claim} 
                  evidence={signal.evidences.find(e => e.id === claim.evidenceId)}
                  variant="favorable"
                />
              ))}
            {signal.favorableEvidenceIds.length === 0 && (
              <p className="text-[12px] text-text-muted italic p-4 bg-surface rounded-sm border border-border">{t.noFavorableEvidence}</p>
            )}
          </div>

          {/* Contradictoria — Columna Secundaria */}
          <div className="md:col-span-2">
            <h3 className="text-[12px] font-mono font-bold text-status-negative-text uppercase tracking-wider flex items-center gap-2 mb-4 border-b border-status-negative-text/20 pb-2">
              <XCircle size={14} />
              {t.contrastingEvidence}
            </h3>
            {signal.claims
              .filter(c => signal.counterEvidenceIds.includes(c.evidenceId))
              .map(claim => (
                <ClaimCard 
                  key={claim.id} 
                  claim={claim} 
                  evidence={signal.evidences.find(e => e.id === claim.evidenceId)}
                  variant="counter"
                />
              ))}
             {signal.counterEvidenceIds.length === 0 && (
              <p className="text-[12px] text-text-muted italic p-4 bg-surface rounded-sm border border-border">{t.noContrastingEvidence}</p>
            )}
          </div>
        </section>
      )}

      {/* 5. SUPUESTOS, INVALIDACIONES Y ACCIONES DE RESEARCH */}
      {isCompleted && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6 border-t border-border">
          <div className="bg-surface border border-border p-4 rounded-sm">
            <h4 className="text-[10px] font-mono font-bold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <CheckCircle2 size={12} className="text-status-positive-text" /> {t.assumptions}
            </h4>
            <div className="space-y-2.5">
              {signal.assumptions.map((a, i) => (
                <div key={i} className="flex gap-2 text-[12px] text-text-secondary leading-relaxed items-start">
                  <CheckCircle2 size={12} className="text-status-positive-text shrink-0 mt-0.5" />
                  <span>{a}</span>
                </div>
              ))}
            </div>
          </div>
          
          <div className="bg-surface border border-border p-4 rounded-sm">
            <h4 className="text-[10px] font-mono font-bold text-text-muted uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <AlertTriangle size={12} className="text-status-negative-text" /> {t.invalidations}
            </h4>
            <div className="space-y-2.5">
              {signal.invalidations.map((a, i) => (
                <div key={i} className="flex gap-2 text-[12px] text-text-secondary leading-relaxed items-start">
                  <AlertTriangle size={12} className="text-status-negative-text shrink-0 mt-0.5" />
                  <span>{a}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface border border-border p-4 rounded-sm border-t-2 border-t-action-accent">
            <h4 className="text-[10px] font-mono font-bold text-action-accent uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Info size={12} className="text-action-accent" /> {t.suggestedActions}
            </h4>
            <div className="space-y-2.5">
              {signal.suggestedResearchActions.map((a, i) => (
                <div key={i} className="flex gap-2 text-[12px] text-text-primary font-medium leading-relaxed items-start">
                  <Info size={12} className="text-action-accent shrink-0 mt-0.5" />
                  <span>{a}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

    </div>
  );
}
