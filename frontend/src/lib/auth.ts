import { createClient, type Session } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim()
const publishableKey = (
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ?? import.meta.env.VITE_SUPABASE_ANON_KEY
)?.trim()
const authEnabled = String(import.meta.env.VITE_AUTH_ENABLED ?? 'false').trim().toLowerCase()

export const isAuthEnabled = ['1', 'true', 'yes'].includes(authEnabled) && Boolean(supabaseUrl && publishableKey)
export const supabase = isAuthEnabled
  ? createClient(supabaseUrl!, publishableKey!, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
    })
  : null

export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data, error } = await supabase.auth.getSession()
  if (error) throw error
  return data.session?.access_token ?? null
}

export type AuthSession = Session
