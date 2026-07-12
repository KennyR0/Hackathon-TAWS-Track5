import { AppProviders } from './providers'
import { AppRouter } from './router'
import { AuthGate } from './AuthGate'

export default function App() {
  return (
    <AppProviders>
      <AuthGate>
        <AppRouter />
      </AuthGate>
    </AppProviders>
  )
}
