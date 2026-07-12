import type { PropsWithChildren, ReactNode } from 'react'
import { AlertTriangle, DatabaseZap, RefreshCw } from 'lucide-react'

export function SurfaceCard({
  title,
  eyebrow,
  action,
  children,
  className = '',
}: PropsWithChildren<{ title?: string; eyebrow?: string; action?: ReactNode; className?: string }>) {
  return (
    <section className={`surface-card ${className}`}>
      {(title || eyebrow || action) && (
        <header className="surface-card__header">
          <div>
            {eyebrow ? <p className="section-eyebrow">{eyebrow}</p> : null}
            {title ? <h2 className="section-title">{title}</h2> : null}
          </div>
          {action ? <div className="surface-card__action">{action}</div> : null}
        </header>
      )}
      {children}
    </section>
  )
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="state-block">
      <DatabaseZap className="state-block__icon" />
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}

export function ErrorState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="state-block state-block--error">
      <AlertTriangle className="state-block__icon" />
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}

export function LoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="skeleton-line" />
      ))}
    </div>
  )
}

export function InlineHint({ children }: PropsWithChildren) {
  return <p className="inline-hint">{children}</p>
}

export function RefreshButton({ onClick, busy = false, label = 'Actualizar' }: { onClick: () => void; busy?: boolean; label?: string }) {
  return (
    <button className="secondary-button" type="button" onClick={onClick} disabled={busy}>
      <RefreshCw size={16} className={busy ? 'spin' : ''} />
      {label}
    </button>
  )
}
