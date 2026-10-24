import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { chatApi, type ChatResponse, type ChatTurn, type PageContext } from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'

// Problem 5: messages go to FastAPI (POST /api/chat), which runs the PydanticAI agent
// (backend/agent.py + prompts/prompt.md).
// Problem 7: when the reply comes with products, they're handed to the page
// ("Will's picks", components/ChatResults.tsx) and the bubble notes how many went up.
// Problem 8: every message also sends the page the shopper is on (so "this" = the open
// product) and their login token. Logged-in shoppers get their saved chat back when they
// open the chat; guests' chat lives only in this window.

interface Message {
  role: 'user' | 'bot'
  text: string
  onPage?: string // e.g. "6 items on the page: Hoodies"
  productIds?: string[] // the cards this reply put on the page
  past?: boolean // reloaded from saved history
}

const noResults = (reply: string): ChatResponse => ({ reply, results_title: null, products: [] })

function greeting(firstName: string | null, returning: boolean): Message {
  if (!firstName) {
    return { role: 'bot', text: "Yo. I'm Will. My cousin runs the place, so technically I work here. Looking for a hoodie or what?" }
  }
  return {
    role: 'bot',
    text: returning
      ? `Yo, ${firstName}. You're back. I remember you, don't worry. What are we looking at today?`
      : `Yo, ${firstName}. I'm Will. My cousin runs the place, so technically I work here. Looking for a hoodie or what?`,
  }
}

// Will sometimes answers with **bold** prices; show those as real bold, never as asterisks.
function withBold(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

function pageContext(pathname: string, search: string): PageContext {
  const m = pathname.match(/^\/products\/([^/]+)$/)
  return { path: pathname + search, product_id: m ? decodeURIComponent(m[1]) : null }
}

export default function ChatWidget() {
  const { user, token, ready } = useAuth()
  const { pathname, search } = useLocation()
  const { show } = useChatResults()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting(null, false)])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  // Who's chatting changed (page load, log in, log out): start this window over.
  // Logged in: reload their saved chat. Guest: just the greeting.
  useEffect(() => {
    if (!ready) return
    if (!user || !token) {
      setMessages([greeting(null, false)])
      return
    }
    let cancelled = false
    chatApi.history(token).then((past) => {
      if (cancelled) return
      const reloaded: Message[] = past.map((h) => ({
        role: h.role === 'user' ? 'user' : 'bot',
        text: h.text,
        past: true,
        onPage: h.product_count ? `${h.product_count} ${h.product_count === 1 ? 'item' : 'items'} shown` : undefined,
      }))
      setMessages([...reloaded, greeting(user.first_name, past.length > 0)])
    })
    return () => { cancelled = true }
  }, [ready, user, token])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  async function sendToBot(text: string): Promise<ChatResponse> {
    // Guests: send this window's earlier messages so Will can follow along (not saved anywhere).
    const guestHistory: ChatTurn[] = token ? [] : messages
      .filter((m) => m !== messages[0])
      .map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', text: m.text, product_ids: m.productIds ?? [] }))
    try {
      return await chatApi.send(text, pageContext(pathname, search), token, guestHistory)
    } catch (err) {
      if (err instanceof TypeError) return noResults("Couldn't reach the chat. Is the backend running?")
      return noResults(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || busy) return
    setDraft('')
    setMessages((m) => [...m, { role: 'user', text }])
    setBusy(true)
    const res = await sendToBot(text)
    let onPage: string | undefined
    if (res.products.length > 0) {
      const title = res.results_title || 'Products'
      show({ title, products: res.products, question: text })
      onPage = `${res.products.length} ${res.products.length === 1 ? 'item' : 'items'} on the page: ${title}`
    }
    setMessages((m) => [...m, { role: 'bot', text: res.reply, onPage, productIds: res.products.map((p) => p.product_id) }])
    setBusy(false)
  }

  const firstPast = messages.findIndex((m) => m.past)

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Shop assistant chat">
          <header className="chat-head">
            <span className="chat-avatar" aria-hidden="true">W</span>
            <div>
              <div className="chat-title">Will · Campus Customs</div>
              <div className="chat-sub">
                {user ? `Chatting as ${user.first_name}. Will remembers your chats.` : "The manager's cousin. Log in and he'll remember you."}
              </div>
            </div>
            <button className="chat-x" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </header>
          <div className="chat-log">
            {messages.map((m, i) => (
              <div key={i} className="bubble-wrap">
                {i === firstPast && <div className="chat-divider">Earlier chats</div>}
                {i > 0 && messages[i - 1].past && !m.past && <div className="chat-divider">Today</div>}
                <div className={`bubble bubble-${m.role}${m.past ? ' past' : ''}`}>
                  {withBold(m.text)}
                  {m.onPage && <div className="bubble-note">{m.past ? '' : '↑ '}{m.onPage}</div>}
                </div>
              </div>
            ))}
            {busy && <div className="bubble bubble-bot typing">Will is checking the back room…</div>}
            <div ref={endRef} />
          </div>
          <form className="chat-form" onSubmit={submit}>
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about a hoodie, size or price…"
              aria-label="Message"
            />
            <button type="submit" disabled={!draft.trim() || busy}>Send</button>
          </form>
        </section>
      )}
      <button className="chat-fab" onClick={() => setOpen(!open)} aria-expanded={open} aria-label={open ? 'Close chat' : 'Open chat'}>
        {open ? '×' : '💬'}
        {!open && <span className="chat-fab-label">Chat with us</span>}
      </button>
    </div>
  )
}
