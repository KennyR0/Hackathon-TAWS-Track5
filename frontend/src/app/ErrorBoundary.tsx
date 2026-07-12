import { Component, type ErrorInfo, type ReactNode } from 'react'

type AppErrorBoundaryProps = {
  children: ReactNode
}

type AppErrorBoundaryState = {
  error: Error | null
}

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    error: null,
  }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('NexoMercado UI runtime error', error, errorInfo)
  }

  render() {
    if (!this.state.error) {
      return this.props.children
    }

    return (
      <main className="app-crash" role="alert">
        <section className="app-crash__panel">
          <p className="section-eyebrow">Interfaz</p>
          <h1>No se pudo renderizar esta pantalla</h1>
          <p>
            Recarga la pagina o vuelve al resumen. El detalle tecnico quedo registrado en la consola del navegador.
          </p>
          <pre>{this.state.error.message}</pre>
          <div className="card-actions">
            <button className="primary-button" type="button" onClick={() => window.location.reload()}>
              Recargar
            </button>
            <a className="secondary-button" href="/summary">
              Volver al resumen
            </a>
          </div>
        </section>
      </main>
    )
  }
}
