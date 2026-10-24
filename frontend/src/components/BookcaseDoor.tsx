import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

// Problem 10 motion: the "secret door". On a shopper's first visit to the Home page, the
// shop sits behind a library bookcase that slides aside to let them in.
// Guardrails: once per visit (sessionStorage), Skip link + Esc / click / scroll / any key
// opens it at once, the slide itself is 1.2s, never shown with "reduce motion" on, and the
// drawing is hidden from screen readers (the page behind is always there for them).

const KEY = 'cc_door_opened'
const HOLD_MS = 900 // a beat to take in the room
const SLIDE_MS = 1200 // the door's travel

const LEATHER = ['#5e1a16', '#6f2419', '#23402f', '#1c3527', '#1d2c4a', '#2b1a12', '#7a4a22', '#4a1420', '#3a2a1a']

function alreadyOpened(): boolean {
  try { return sessionStorage.getItem(KEY) === '1' } catch { return false }
}
function markOpened() {
  try { sessionStorage.setItem(KEY, '1') } catch { /* private mode: plays again next load, that's fine */ }
}
function reducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

// Same books every time: a tiny seeded random number generator.
function rng(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296
    return seed / 4294967296
  }
}

interface Book { w: number; h: number; color: string; lean: number; bands: boolean }

function makeShelves(): Book[][] {
  const r = rng(1973)
  return Array.from({ length: 5 }, () => {
    const books: Book[] = []
    let width = 0
    while (width < 1700) {
      const w = 14 + Math.round(r() * 24)
      books.push({
        w,
        h: 68 + Math.round(r() * 27),
        color: LEATHER[Math.floor(r() * LEATHER.length)],
        lean: r() < 0.06 ? (r() < 0.5 ? -7 : 7) : 0,
        bands: r() < 0.8,
      })
      width += w + 2
    }
    return books
  })
}

export default function BookcaseDoor() {
  const { pathname } = useLocation()
  const [state, setState] = useState<'closed' | 'opening' | 'gone'>(() =>
    pathname === '/' && !alreadyOpened() && !reducedMotion() ? 'closed' : 'gone',
  )
  const shelves = useMemo(makeShelves, [])
  const timers = useRef<number[]>([])

  const open = () => {
    setState((s) => {
      if (s !== 'closed') return s
      markOpened()
      timers.current.push(window.setTimeout(() => setState('gone'), SLIDE_MS))
      return 'opening'
    })
  }

  useEffect(() => {
    if (state !== 'closed') return
    timers.current.push(window.setTimeout(open, HOLD_MS))
    const now = () => open()
    window.addEventListener('keydown', now)
    window.addEventListener('wheel', now, { passive: true })
    window.addEventListener('touchmove', now, { passive: true })
    return () => {
      window.removeEventListener('keydown', now)
      window.removeEventListener('wheel', now)
      window.removeEventListener('touchmove', now)
    }
  }, [state])

  useEffect(() => () => timers.current.forEach(clearTimeout), [])

  // Leaving Home before it opens counts as opened.
  useEffect(() => { if (pathname !== '/' && state === 'closed') { markOpened(); setState('gone') } }, [pathname, state])

  if (state === 'gone') return null

  return (
    <div className={`door-stage ${state}`} onClick={open} style={{ ['--slide-ms' as string]: `${SLIDE_MS}ms` }}>
      <div className="bookcase" aria-hidden="true">
        <div className="bookcase-crown" />
        {shelves.map((books, i) => (
          <div key={i} className="shelf">
            <div className="shelf-books">
              {books.map((b, j) => (
                <span
                  key={j}
                  className={`book${b.bands ? ' banded' : ''}`}
                  style={{ width: b.w, height: `${b.h}%`, background: b.color, transform: b.lean ? `rotate(${b.lean}deg)` : undefined }}
                />
              ))}
            </div>
            {i === 2 && <span className="bookcase-plaque">Campus Customs<em>on Broadway since 1973</em></span>}
          </div>
        ))}
        <div className="bookcase-light" />
      </div>
      <button className="door-skip" onClick={(e) => { e.stopPropagation(); open() }}>Skip</button>
    </div>
  )
}
