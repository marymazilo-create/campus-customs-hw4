import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

// "Will's picks": the product cards the chat put on the page (Problem 7).
// The cards are the same ProductCard used on the Products page, so clicking one opens the
// Problem 3 product page (/products/:id) with the large image and full details.
// On a product page the section folds down to one line so the product stays front and center.

const SHOP_CATEGORIES = ['Hoodies', 'Crewnecks', 'Tees & Tops', 'Quarter-Zips', 'Jackets']

export default function ChatResults() {
  const { results, clear } = useChatResults()
  const { pathname } = useLocation()
  const onProductPage = /^\/products\/[^/]+$/.test(pathname)
  const [open, setOpen] = useState(true)
  const ref = useRef<HTMLElement>(null)

  // New results: open the section and bring it into view.
  useEffect(() => {
    if (!results) return
    setOpen(true)
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [results?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Clicked into a product: fold the picks away (one click brings them back).
  useEffect(() => {
    if (onProductPage) setOpen(false)
  }, [pathname, onProductPage])

  if (!results) return null
  const { title, products, question } = results
  const category = SHOP_CATEGORIES.find((c) => c.toLowerCase() === title.toLowerCase())
  const current = onProductPage ? decodeURIComponent(pathname.split('/')[2]) : ''

  return (
    <section ref={ref} className={`chat-results container${open ? '' : ' folded'}`} aria-label="Will's picks from the chat">
      <div className="chat-results-head">
        <div>
          <p className="eyebrow">Will's picks · from the chat</p>
          <h2 className="chat-results-title">
            {title} <span className="chat-results-count">({products.length})</span>
          </h2>
          {open && question && <p className="muted chat-results-q">You asked: “{question}”</p>}
        </div>
        <div className="chat-results-actions">
          {open && category && (
            <Link className="text-link" to={`/products?category=${encodeURIComponent(category)}`}>See all {category} →</Link>
          )}
          <button className="link-btn" onClick={() => setOpen(!open)}>{open ? 'Hide' : 'Show'}</button>
          <button className="link-btn" onClick={clear}>Clear</button>
        </div>
      </div>
      {open && (
        <div className="grid">
          {products.map((p) => (
            <div key={p.product_id} className={p.product_id === current ? 'chat-pick current' : 'chat-pick'}>
              <ProductCard product={p} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
