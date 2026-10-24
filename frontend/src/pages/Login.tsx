import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import { useAuth } from '../auth'

export default function Login() {
  const { signIn, user } = useAuth()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      signIn(await authApi.login({ email, password }))
      navigate(from, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="container page auth">
        <h1 className="page-title">You're logged in</h1>
        <p>Signed in as <strong>{user.email}</strong>.</p>
        <Link to="/products" className="btn btn-primary">Keep shopping</Link>
      </div>
    )
  }

  return (
    <div className="container page auth">
      <h1 className="page-title">Log in</h1>
      <p className="muted">Welcome back! Log in so our shop assistant can remember your chats.</p>
      <form className="form" onSubmit={submit} noValidate>
        <label>Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
        </label>
        <label>Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={busy || !email || !password}>
          {busy ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      <p className="muted">New here? <Link to="/create-account">Create an account</Link></p>
    </div>
  )
}
