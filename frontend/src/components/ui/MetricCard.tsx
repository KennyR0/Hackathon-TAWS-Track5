interface MetricCardProps {
  label: string;
  value: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  meta?: string;
  accentColor?: string; // Tailwind color class for the top border
}

export const MetricCard = ({ label, value, trend, trendValue, meta, accentColor }: MetricCardProps) => {
  return (
    <div className={`flex flex-col p-4 bg-surface border border-border rounded-sm ${accentColor ? `border-t-2 ${accentColor}` : ''}`}>
      <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
        {label}
      </span>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-mono font-bold tracking-tight text-text-primary tabular-nums">
          {value}
        </span>
        {trend && (
          <span
            className={`text-[12px] font-mono font-bold flex items-center gap-0.5 ${
              trend === 'up' ? 'text-status-positive-text' :
              trend === 'down' ? 'text-status-negative-text' :
              'text-text-secondary'
            }`}
          >
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
            {trendValue && <span>{trendValue}</span>}
          </span>
        )}
      </div>
      {meta && (
        <span className="mt-1.5 text-[11px] text-text-secondary">
          {meta}
        </span>
      )}
    </div>
  );
};
