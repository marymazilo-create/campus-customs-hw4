import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Audience, type Category, type ProductCard as Card } from '../api'
import ProductCard from '../components/ProductCard'

// DRAFT copy for Mary to review: written in our own words, inspired by yalebulldogblue.com.
const FEATURED = [
  'basic-hoodie-big-yale',
  '2025-yale-vs-harvard-t-shirt',
  'baseball-left-chest-crewneck',
  'big-yale-tri-blend-t-shirt',
]

const CATEGORY_IMAGES: Record<string, string> = {
  Hoodies: '/images/basic-hoodie-big-yale.jpg',
  Crewnecks: '/images/baseball-left-chest-crewneck.jpg',
  'Tees & Tops': '/images/boola-boola-t-shirt.jpg',
  'Quarter-Zips': '/images/branford-1-4-zip.jpg',
  Jackets: '/images/berkeley-sweater-fleece-jacket.jpg',
}

export default function Home() {
  const [featured, setFeatured] = useState<Card[]>([])
  const [cats, setCats] = useState<Category[]>([])
  const [groups, setGroups] = useState<Audience[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.products()
      .then((all) => {
        const picks = FEATURED.map((id) => all.find((p) => p.product_id === id)).filter(Boolean) as Card[]
        setFeatured(picks.length ? picks : all.slice(0, 4))
      })
      .catch(() => setError('The shop is offline right now. Is the backend running?'))
    api.categories().then(setCats).catch(() => {})
    api.audiences().then(setGroups).catch(() => {})
  }, [])

  return (
    <>
      <section className="hero panel-wall">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">Officially licensed Yale gear, 57 Broadway</p>
            <h1>Yale, worn well since 1973.</h1>
            <p className="hero-lead">
              Hoodies, crewnecks, tees and layers for students, alumni, families and fans,
              from the Broadway shop that's been dressing Bulldogs since 1973.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-primary">Shop all gear</Link>
              <Link to="/about" className="btn btn-ghost">Our story</Link>
            </div>
          </div>
          {/* Problem 10: the shop's favorites hung like portraits on the paneled wall */}
          <div className="hero-gallery">
            {FEATURED.slice(0, 3).map((id) => {
              const p = featured.find((f) => f.product_id === id)
              return (
                <Link key={id} to={`/products/${id}`} className="hero-frame-link" aria-label={p?.name ?? 'Featured product'}>
                  <span className="frame"><span className="frame-mat"><img src={`/images/${id}.jpg`} alt="" /></span></span>
                  {p && <span className="frame-caption">{p.name}</span>}
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      <section className="section container">
        <h2 className="section-title">Shop by category</h2>
        <div className="cat-grid">
          {cats.map((c) => (
            <Link key={c.name} to={`/products?category=${encodeURIComponent(c.name)}`} className="cat-tile">
              {CATEGORY_IMAGES[c.name] && <img src={CATEGORY_IMAGES[c.name]} alt="" loading="lazy" />}
              <span className="cat-name">{c.name}</span>
              <span className="cat-count">{c.count} styles</span>
            </Link>
          ))}
        </div>
      </section>

      {groups.length > 0 && (
        <section className="section container">
          <h2 className="section-title">Shop for…</h2>
          <p className="muted section-lead">Gifts for the whole Yale family, your college, your school or your team.</p>
          <div className="who-grid">
            {groups.map((g) => (
              <Link key={g.key} to={`/products?for=${g.key}`} className="who-tile">
                <img src={g.image_url} alt="" loading="lazy" />
                <span className="who-label">{g.label}</span>
                <span className="who-blurb">{g.blurb}</span>
                <span className="cat-count">{g.count} {g.count === 1 ? 'style' : 'styles'}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="section container">
        <div className="section-row">
          <h2 className="section-title">Bulldog favorites</h2>
          <Link to="/products" className="text-link">View all →</Link>
        </div>
        {error && <p className="notice">{error}</p>}
        <div className="grid">
          {featured.map((p) => <ProductCard key={p.product_id} product={p} />)}
        </div>
      </section>

      <section className="band">
        <div className="container band-inner">
          <div>
            <h2>Something for every Yalie</h2>
            <p>Find your residential college, your team, your grad school, or a gift for Yale Mom, Dad and Grandpa.</p>
          </div>
          <Link to="/products" className="btn btn-light">Browse the collection</Link>
        </div>
      </section>

      <section className="section container visit">
        <div>
          <h2 className="section-title">Come visit us</h2>
          <p>57 Broadway, New Haven, CT 06511. Steps from Old Campus. Stop in to try on sizes, or ask our chat assistant anytime.</p>
        </div>
      </section>
    </>
  )
}
