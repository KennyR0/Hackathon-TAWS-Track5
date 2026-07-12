import { AppErrorBoundary } from './ErrorBoundary'
import { AppProviders } from './providers'
import { AppRouter } from './router'
import { AuthGate } from './AuthGate'

export default function App() {
  return (
    <AppErrorBoundary>
      <AppProviders>
        <AuthGate>
          <AppRouter />
        </AuthGate>
      </AppProviders>
    </AppErrorBoundary>
  )
}
