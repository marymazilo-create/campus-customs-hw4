import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import { useAuth } from '../auth'

const MIN_LEN = 8

export default function CreateAccount() {
  const { signIn, user } = useAuth()
  const navigate = useNavigate()
  const [f, setF] = useState({ first_name: '', last_name: '', email: '', password: '', confirm_password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value })

  const tooShort = f.password.length > 0 && f.password.length < MIN_LEN
  const mismatch = f.confirm_password.length > 0 && f.password !== f.confirm_password

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (f.password.length < MIN_LEN) return setError(`Password must be at least ${MIN_LEN} characters.`)
    if (f.password !== f.confirm_password) return setError("Passwords don't match.")
    setBusy(true)
    try {
      signIn(await authApi.signup(f))
      navigate('/', { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (user) {
    return (
      <div className="container page auth">
        <h1 className="page-title">You already have an account</h1>
        <p>Signed in as <strong>{user.email}</strong>.</p>
        <Link to="/products" className="btn btn-primary">Keep shopping</Link>
      </div>
    )
  }

  return (
    <div className="container page auth">
      <h1 className="page-title">Create account</h1>
      <p className="muted">Save your chats with our shop assistant and check out faster next time.</p>
      <form className="form" onSubmit={submit} noValidate>
        <div className="form-row">
          <label>First name<input value={f.first_name} onChange={set('first_name')} autoComplete="given-name" required /></label>
          <label>Last name<input value={f.last_name} onChange={set('last_name')} autoComplete="family-name" required /></label>
        </div>
        <label>Email<input type="email" value={f.email} onChange={set('email')} autoComplete="email" required /></label>
        <label>Password
          <input type="password" value={f.password} onChange={set('password')} autoComplete="new-password" required />
          <span className={`hint ${tooShort ? 'hint-bad' : ''}`}>At least {MIN_LEN} characters</span>
        </label>
        <label>Confirm password
          <input type="password" value={f.confirm_password} onChange={set('confirm_password')} autoComplete="new-password" required />
          {mismatch && <span className="hint hint-bad">Passwords don't match</span>}
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button
          className="btn btn-primary"
          type="submit"
          disabled={busy || !f.first_name || !f.last_name || !f.email || !f.password || !f.confirm_password}
        >
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">Already have an account? <Link to="/login">Log in</Link></p>
    </div>
  )
}
