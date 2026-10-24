// Types and calls for the FastAPI backend (backend/main.py).

export type StockStatus = 'in_stock' | 'low_stock' | 'sold_out'

export interface ProductCard {
  product_id: string
  name: string
  garment_type: string
  category: string
  short_description: string
  price: number
  image_url: string
  in_stock: boolean
  // Problem 9 "My size": set when a size is picked
  size?: string | null
  size_quantity?: number | null
  size_status?: StockStatus | null
}

export interface Audience {
  key: string
  label: string
  blurb: string
  count: number
  image_url: string
}

export interface SizeStock {
  size: string
  quantity: number
  status: StockStatus
}

export interface ProductDetail extends ProductCard {
  description: string
  colors: string[]
  tags: string[]
  sizes: SizeStock[]
  total_stock: number
}

export interface Category {
  name: string
  count: number
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const api = {
  products: (params: { q?: string; category?: string; for?: string; size?: string } = {}) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    if (params.category) qs.set('category', params.category)
    if (params.for) qs.set('for', params.for)
    if (params.size) qs.set('size', params.size)
    const s = qs.toString()
    return get<ProductCard[]>(`/api/products${s ? `?${s}` : ''}`)
  },
  product: (id: string) => get<ProductDetail>(`/api/products/${encodeURIComponent(id)}`),
  categories: () => get<Category[]>('/api/categories'),
  audiences: () => get<Audience[]>('/api/audiences'),
}

export const money = (n: number) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

// ---------- accounts (Problem 4) ----------

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface Session {
  token: string
  user: User
}

async function send<T>(path: string, body: unknown, token?: string | null): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body ?? {}),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail
    throw new Error(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.')
  }
  return data as T
}

export const authApi = {
  signup: (b: { first_name: string; last_name: string; email: string; password: string; confirm_password: string }) =>
    send<Session>('/api/auth/signup', b),
  login: (b: { email: string; password: string }) => send<Session>('/api/auth/login', b),
  logout: (token: string) => send<{ ok: boolean }>('/api/auth/logout', {}, token),
  me: async (token: string): Promise<User | null> => {
    const res = await fetch('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
    return res.ok ? ((await res.json()) as User) : null
  },
}

// ---------- chat (Problem 5) ----------
// The chat widget POSTs to FastAPI's /api/chat, which runs the PydanticAI agent.

// The chat -> page contract (Problem 7). The agent picks product_ids; the backend turns
// them into real cards from the database; the page shows them in "Will's picks".
export interface ChatResponse {
  reply: string // the chat bubble
  results_title: string | null // heading for the cards on the page; null = leave the page alone
  products: ProductCard[] // real cards from the database, in the agent's order
}

// Problem 8: the page the shopper is on, plus (guests only) the open chat window.
// Logged-in shoppers send their login token instead; their history lives in the database.
export interface PageContext {
  path: string
  product_id: string | null
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  text: string
  product_ids?: string[] // cards that reply put on the page ("the second one")
}

export interface HistoryMessage {
  role: 'user' | 'assistant'
  text: string
  product_count: number
  created_at: string
}

export const chatApi = {
  send: (message: string, page: PageContext, token: string | null, guestHistory: ChatTurn[] = []) =>
    send<ChatResponse>('/api/chat', { message, page, guest_history: token ? [] : guestHistory }, token),
  history: async (token: string): Promise<HistoryMessage[]> => {
    const res = await fetch('/api/chat/history', { headers: { Authorization: `Bearer ${token}` } })
    return res.ok ? ((await res.json()) as HistoryMessage[]) : []
  },
}
