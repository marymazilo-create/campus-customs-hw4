import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi, type Session, type User } from './api'

// Keeps track of who is logged in. Only the random session token is kept in the
// browser (never the password); the server looks the user up from it.

const KEY = 'cc_session_token'

function readToken(): string | null {
  try { return localStorage.getItem(KEY) } catch { return null }
}
function writeToken(token: string | null) {
  try { token ? localStorage.setItem(KEY, token) : localStorage.removeItem(KEY) } catch { /* private mode */ }
}

interface AuthState {
  user: User | null
  token: string | null
  ready: boolean
  signIn: (s: Session) => void
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken)
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!token) { setReady(true); return }
    authApi.me(token)
      .then((u) => { if (u) setUser(u); else { writeToken(null); setToken(null) } })
      .catch(() => {})
      .finally(() => setReady(true))
    // only on first load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const signIn = (s: Session) => {
    writeToken(s.token)
    setToken(s.token)
    setUser(s.user)
  }

  const signOut = async () => {
    if (token) await authApi.logout(token).catch(() => {})
    writeToken(null)
    setToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, token, ready, signIn, signOut }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
