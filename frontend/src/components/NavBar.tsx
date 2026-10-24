import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const close = () => setOpen(false)

  return (
    <header className="site-header">
      <div className="announce">Officially licensed Yale gear · On Broadway in New Haven since 1973</div>
      <nav className="nav container" aria-label="Main">
        <Link to="/" className="brand" onClick={close} aria-label="Campus Customs home">
          <span className="brand-yale">YALE</span>
          <span className="brand-sub">Campus Customs on Broadway</span>
        </Link>

        <button className="nav-toggle" aria-expanded={open} aria-controls="nav-links" onClick={() => setOpen(!open)}>
          <span className="sr-only">Menu</span>☰
        </button>

        <div id="nav-links" className={`nav-links ${open ? 'open' : ''}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav-spacer" />
          {user ? (
            <>
              <span className="nav-user">Hi, {user.first_name}</span>
              <button
                className="nav-logout"
                onClick={async () => { close(); await signOut(); navigate('/') }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>Log in</NavLink>
              <NavLink to="/create-account" className="nav-cta" onClick={close}>Create account</NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
