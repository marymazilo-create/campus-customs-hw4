import { useCallback, useEffect, useState } from 'react'

// Problem 9 "My size": the shopper's size, remembered in this browser between visits.
// Stored locally (not on the account) so it works for guests too.

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL'] as const
const KEY = 'cc_my_size'
const EVENT = 'cc-my-size'

function read(): string {
  try {
    const v = localStorage.getItem(KEY) ?? ''
    return (SIZES as readonly string[]).includes(v) ? v : ''
  } catch {
    return ''
  }
}

export function useMySize(): [string, (size: string) => void] {
  const [size, setSize] = useState(read)
  useEffect(() => {
    const sync = () => setSize(read())
    window.addEventListener(EVENT, sync)
    return () => window.removeEventListener(EVENT, sync)
  }, [])
  const update = useCallback((next: string) => {
    try {
      if (next) localStorage.setItem(KEY, next)
      else localStorage.removeItem(KEY)
    } catch { /* private mode: still works for this visit */ }
    setSize(next)
    window.dispatchEvent(new Event(EVENT))
  }, [])
  return [size, update]
}
