import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type Audience, type Category, type ProductCard as Card } from '../api'
import ProductCard from '../components/ProductCard'
import { SIZES, useMySize } from '../mySize'

// Problem 9 adds two filters next to search and category:
//   Shop for  (?for=mom): gift lines and groups like Mom, Dad, Residential Colleges
//   My size   (remembered): only items in stock in that size, with the size's stock on each card

export default function Products() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const category = params.get('category') ?? ''
  const audience = params.get('for') ?? ''
  const [mySize, setMySize] = useMySize()
  const [draft, setDraft] = useState(q)
  const [products, setProducts] = useState<Card[] | null>(null)
  const [cats, setCats] = useState<Category[]>([])
  const [groups, setGroups] = useState<Audience[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.categories().then(setCats).catch(() => {})
    api.audiences().then(setGroups).catch(() => {})
  }, [])

  useEffect(() => {
    setProducts(null)
    setError('')
    api.products({ q, category, for: audience, size: mySize })
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running on port 8000?'))
  }, [q, category, audience, mySize])

  function update(next: { q?: string; category?: string; for?: string }) {
    const p = new URLSearchParams(params)
    for (const [k, v] of Object.entries(next)) {
      if (v) p.set(k, v)
      else p.delete(k)
    }
    setParams(p)
  }

  const group = groups.find((g) => g.key === audience)

  return (
    <div className="container page">
      <h1 className="page-title">{group ? `Shop ${group.label}` : 'Shop Yale gear'}</h1>

      <div className="toolbar">
        <form className="search" onSubmit={(e) => { e.preventDefault(); update({ q: draft.trim() }) }}>
          <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Search hoodies, Branford, baseball…" aria-label="Search products" />
          <button type="submit">Search</button>
        </form>
        <div className="filter-row">
          <span className="filter-label">Type</span>
          <div className="chips" role="group" aria-label="Category">
            <button className={!category ? 'chip active' : 'chip'} onClick={() => update({ category: '' })}>All</button>
            {cats.map((c) => (
              <button key={c.name} className={category === c.name ? 'chip active' : 'chip'} onClick={() => update({ category: c.name })}>
                {c.name}
              </button>
            ))}
          </div>
        </div>
        <div className="filter-row">
          <span className="filter-label">Shop for</span>
          <div className="chips" role="group" aria-label="Shop for">
            <button className={!audience ? 'chip active' : 'chip'} onClick={() => update({ for: '' })}>Everyone</button>
            {groups.map((g) => (
              <button key={g.key} className={audience === g.key ? 'chip active' : 'chip'} onClick={() => update({ for: g.key })}>
                {g.label}
              </button>
            ))}
          </div>
        </div>
        <div className="filter-row">
          <span className="filter-label">My size</span>
          <div className="chips" role="group" aria-label="My size">
            <button className={!mySize ? 'chip active' : 'chip'} onClick={() => setMySize('')}>Any</button>
            {SIZES.map((s) => (
              <button key={s} className={mySize === s ? 'chip active size-chip' : 'chip size-chip'} onClick={() => setMySize(s)} aria-pressed={mySize === s}>
                {s}
              </button>
            ))}
          </div>
          {mySize && <span className="filter-hint">Showing only what's in stock in {mySize}. We'll remember your size.</span>}
        </div>
      </div>

      {error && <p className="notice">{error}</p>}
      {products && (
        <p className="result-count">
          {products.length} {products.length === 1 ? 'item' : 'items'}
          {mySize && <> in stock in {mySize}</>}
          {group && <> for {group.label.replace(/^For /, '')}</>}
          {q && <> for “{q}” <button className="link-btn" onClick={() => { setDraft(''); update({ q: '' }) }}>clear</button></>}
        </p>
      )}
      {!products && !error && <p className="muted">Loading…</p>}
      <div className="grid">
        {products?.map((p) => <ProductCard key={p.product_id} product={p} />)}
      </div>
      {products?.length === 0 && (
        <p className="muted">
          No matches{mySize ? ` in ${mySize}` : ''}.{' '}
          {mySize ? <button className="link-btn" onClick={() => setMySize('')}>Show all sizes</button> : 'Try another word or filter.'}
        </p>
      )}
    </div>
  )
}
