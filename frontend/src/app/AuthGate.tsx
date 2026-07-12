import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { LogIn } from 'lucide-react'

import { isAuthEnabled, supabase, type AuthSession } from '../lib/auth'

export function AuthGate({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [isLoading, setIsLoading] = useState(isAuthEnabled)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!supabase) return
    let isMounted = true
    void supabase.auth.getSession().then(({ data }) => {
      if (isMounted) {
        setSession(data.session)
        setIsLoading(false)
      }
    })
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setIsLoading(false)
    })
    return () => {
      isMounted = false
      data.subscription.unsubscribe()
    }
  }, [])

  if (!isAuthEnabled) return children
  if (isLoading) return <main className="auth-page">Validando sesion...</main>
  if (session) return children

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setError(null)
    setIsLoading(true)
    const { error: signInError } = await supabase!.auth.signInWithPassword({
      email: String(form.get('email') ?? ''),
      password: String(form.get('password') ?? ''),
    })
    setIsLoading(false)
    if (signInError) setError('No se pudo iniciar sesion con esas credenciales.')
  }

  return (
    <main className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>NexoMercado AI</h1>
        <label>
          Correo
          <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Contrasena
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {error ? <p role="alert">{error}</p> : null}
        <button type="submit" disabled={isLoading}>
          <LogIn size={18} aria-hidden="true" />
          Ingresar
        </button>
      </form>
    </main>
  )
}
