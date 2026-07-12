import { useState, useEffect } from 'react';
import { getAgentRun } from '../lib/mockData';
import type { AgentRun } from '../lib/types';
import { Terminal, Clock, Activity, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { TRANSLATIONS } from '../lib/translations';

function formatLogTime(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}.${d.getMilliseconds().toString().padStart(3, '0')}`;
}

export function Audit() {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      try {
        const data = await getAgentRun('run_01hx_44mk');
        setRun(data);
      } catch (e) {
        console.error(e);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const t = TRANSLATIONS.audit;

  if (isLoading) {
    return <div className="p-8 font-mono text-[12px] text-accent-audit animate-pulse">{t.connectingStream}</div>;
  }

  if (!run) {
    return <div className="p-8 text-center text-[13px] text-status-negative-text">{t.errorLoading}</div>;
  }

  const durationMs = run.completedAt && run.startedAt 
    ? new Date(run.completedAt).getTime() - new Date(run.startedAt).getTime() 
    : 0;

  return (
    <div className="max-w-5xl mx-auto flex flex-col h-full font-mono">
      
      {/* HEADER DE OPERADOR — acento terracota/ladrillo */}
      <div className="bg-surface border border-border border-t-2 border-t-accent-audit p-4 rounded-t-sm shrink-0 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-[13px] font-bold text-text-primary uppercase tracking-wider flex items-center gap-2">
            <Terminal size={14} className="text-accent-audit" /> {t.consoleHeader}
          </h2>
          <div className="text-[10px] text-text-muted mt-1.5 flex items-center gap-3">
            <span>{t.runId} <span className="font-bold text-accent-audit">{run.id}</span></span>
            <span>{t.signalId} <span className="font-bold text-text-secondary">{run.signalId}</span></span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-[10px] uppercase">
          {/* DataMode de la ejecución */}
          <div className="flex flex-col items-end">
            <span className="text-text-muted">{t.mode}</span>
            <span className={`font-bold border border-current px-1 mt-0.5 rounded-sm ${
              run.dataMode === 'fixture' ? 'text-status-uncertain-text' :
              run.dataMode === 'live' ? 'text-status-positive-text' :
              'text-status-negative-text'
            }`}>
              {TRANSLATIONS.dataModes[run.dataMode]}
            </span>
          </div>

          {/* Estado Global */}
          <div className="flex flex-col items-end">
            <span className="text-text-muted">{t.status}</span>
            <div className="flex items-center gap-1 mt-0.5 font-bold">
              {run.status === 'running' && <Loader2 size={10} className="animate-spin text-accent-audit" />}
              <span className={
                run.status === 'completed' ? 'text-status-positive-text' :
                run.status === 'failed' ? 'text-status-negative-text' :
                'text-accent-audit'
              }>{TRANSLATIONS.statuses[run.status]}</span>
            </div>
          </div>

          <div className="flex flex-col items-end">
            <span className="text-text-muted">{t.duration}</span>
            <span className="font-bold mt-0.5 flex items-center gap-1 text-accent-audit">
              <Clock size={10} /> {durationMs}ms
            </span>
          </div>
        </div>
      </div>

      {/* TIMELINE / LOG DE PASOS */}
      <div className="flex-1 overflow-auto bg-surface border-x border-b border-border rounded-b-sm p-4 md:p-6 text-[12px] space-y-4">
        
        {run.steps.map((step, idx) => {
          const { id, nodeName, status, startedAt, completedAt, ...extraProps } = step;
          
          const stepDuration = startedAt && completedAt 
            ? new Date(completedAt).getTime() - new Date(startedAt).getTime()
            : null;

          return (
            <div key={id} className="flex gap-4 relative group">
              
              {/* Eje / Línea conectora — terracota */}
              {idx !== run.steps.length - 1 && (
                <div className="absolute top-7 bottom-[-16px] left-[9px] w-px bg-accent-audit/20 group-hover:bg-accent-audit/40 transition-colors z-0" />
              )}
              
              {/* Nodo visual con iconos de estado */}
              <div className="relative z-10 shrink-0 mt-1">
                <div className={`w-5 h-5 rounded-sm border flex items-center justify-center ${
                  status === 'success' ? 'border-status-positive-text bg-status-positive-bg' :
                  status === 'running' ? 'border-accent-audit bg-accent-audit/10' :
                  status === 'error' ? 'border-status-negative-text bg-status-negative-bg' :
                  'border-border bg-surface'
                }`}>
                  {status === 'success' && <CheckCircle2 size={11} className="text-status-positive-text" />}
                  {status === 'running' && <Loader2 size={11} className="animate-spin text-accent-audit" />}
                  {status === 'error' && <XCircle size={11} className="text-status-negative-text" />}
                  {status === 'pending' && <Clock size={11} className="text-text-muted" />}
                </div>
              </div>

              {/* Información del Paso */}
              <div className="flex-1 bg-bg border border-border p-3 rounded-sm hover:border-accent-audit/30 transition-colors">
                <div className="flex flex-wrap md:flex-nowrap items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[12px] text-text-primary">{nodeName}</span>
                    <span className={`text-[9px] uppercase px-1.5 py-0.2 border rounded-sm font-bold ${
                      status === 'success' ? 'border-status-positive-text/30 text-status-positive-text' :
                      status === 'error' ? 'border-status-negative-text/30 text-status-negative-text' :
                      status === 'running' ? 'border-accent-audit/30 text-accent-audit animate-pulse' :
                      'border-border text-text-muted'
                    }`}>
                      {TRANSLATIONS.statuses[status]}
                    </span>
                  </div>
                  
                  {/* Tiempos */}
                  <div className="text-[10px] text-text-muted flex gap-3 text-right shrink-0">
                    {startedAt && <span className="text-accent-audit/70">{formatLogTime(startedAt)}</span>}
                    {stepDuration !== null && <span className="text-text-secondary">({stepDuration}ms)</span>}
                  </div>
                </div>

                {/* Propiedades arbitrarias (Forward compatibility) */}
                {Object.keys(extraProps).length > 0 && (
                  <div className="mt-2 bg-surface-elevated/40 border border-border/40 rounded-sm p-2 overflow-x-auto text-[11px]">
                    <table className="w-full text-left">
                      <tbody>
                        {Object.entries(extraProps).map(([key, val]) => (
                          <tr key={key} className="border-b border-border/10 last:border-0">
                            <td className="py-1 pr-4 font-bold text-accent-audit/70 uppercase w-1/4">{key}</td>
                            <td className="py-1 text-text-secondary">{String(val)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {run.status === 'completed' && (
          <div className="flex items-center gap-3 text-[10px] text-text-muted mt-6 italic pl-8">
            <Activity size={10} /> {t.timelineEnd}
          </div>
        )}
      </div>
    </div>
  );
}
