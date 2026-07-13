export function NewsSourceLink({
  url,
  linkable,
  label = 'Leer fuente',
  demoLabel = 'Demo · sin enlace externo',
}: {
  url: string
  linkable: boolean
  label?: string
  demoLabel?: string
}) {
  if (linkable) {
    return (
      <a className="text-link" href={url} rel="noreferrer" target="_blank">
        {label}
      </a>
    )
  }
  return <span className="news-source-muted">{demoLabel}</span>
}
