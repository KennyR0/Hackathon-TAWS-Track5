export type BadgeType = 
  | 'positive' | 'negative' | 'neutral' | 'uncertain'
  | 'pending_review' | 'reviewed' | 'escalated' | 'discarded';

interface StatusBadgeProps {
  type: BadgeType;
  label?: string;
}

const badgeConfig: Record<BadgeType, { bg: string; border: string; text: string; dot: string; label: string }> = {
  positive:       { bg: 'bg-status-positive-bg', border: 'border-status-positive-text/20', text: 'text-status-positive-text', dot: 'bg-status-positive-text', label: 'Positivo' },
  negative:       { bg: 'bg-status-negative-bg', border: 'border-status-negative-text/20', text: 'text-status-negative-text', dot: 'bg-status-negative-text', label: 'Negativo' },
  neutral:        { bg: 'bg-status-neutral-bg',  border: 'border-status-neutral-text/20',  text: 'text-status-neutral-text',  dot: 'bg-status-neutral-text',  label: 'Neutral' },
  uncertain:      { bg: 'bg-status-uncertain-bg', border: 'border-status-uncertain-text/20', text: 'text-status-uncertain-text', dot: 'bg-status-uncertain-text', label: 'Incierto' },
  pending_review: { bg: 'bg-status-uncertain-bg', border: 'border-status-uncertain-text/20', text: 'text-status-uncertain-text', dot: 'bg-status-uncertain-text', label: 'Pendiente' },
  reviewed:       { bg: 'bg-status-positive-bg', border: 'border-status-positive-text/20', text: 'text-status-positive-text', dot: 'bg-status-positive-text', label: 'Revisado' },
  escalated:      { bg: 'bg-status-negative-bg', border: 'border-status-negative-text/20', text: 'text-status-negative-text', dot: 'bg-status-negative-text', label: 'Escalado' },
  discarded:      { bg: 'bg-status-neutral-bg opacity-50', border: 'border-status-neutral-text/10', text: 'text-text-muted', dot: 'bg-text-muted', label: 'Descartado' },
};

export const StatusBadge = ({ type, label }: StatusBadgeProps) => {
  const config = badgeConfig[type];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm px-1.5 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase select-none border ${config.bg} ${config.border} ${config.text}`}
    >
      <span className={`w-1.5 h-1.5 shrink-0 ${config.dot}`} />
      {label || config.label}
    </span>
  );
};
