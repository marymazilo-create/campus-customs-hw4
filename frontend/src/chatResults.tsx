import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import type { ProductCard } from './api'

// Shared between the chat widget (which fills it) and the "Will's picks" section on the
// page (which shows it). Lives above the routes, so the picks survive clicking into a
// product page and coming back.

export interface ChatResults {
  title: string
  products: ProductCard[]
  question: string // what the shopper asked, shown under the heading
  id: number // changes every time new results arrive
}

interface ChatResultsState {
  results: ChatResults | null
  show: (r: Omit<ChatResults, 'id'>) => void
  clear: () => void
}

const Ctx = createContext<ChatResultsState | null>(null)

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(null)
  const show = useCallback((r: Omit<ChatResults, 'id'>) => setResults({ ...r, id: Date.now() }), [])
  const clear = useCallback(() => setResults(null), [])
  return <Ctx.Provider value={{ results, show, clear }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useChatResults(): ChatResultsState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
