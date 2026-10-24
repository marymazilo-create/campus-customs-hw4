import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, money, type ProductDetail, type SizeStock } from '../api'
import { useMySize } from '../mySize'

const STATUS_LABEL: Record<SizeStock['status'], string> = {
  in_stock: 'In stock',
  low_stock: 'Only a few left',
  sold_out: 'Sold out',
}

export default function ProductPage() {
  const { id = '' } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [error, setError] = useState('')
  const [size, setSize] = useState<string>('')
  const [mySize] = useMySize()

  useEffect(() => {
    setProduct(null)
    setError('')
    setSize('')
    api.product(id)
      .then((p) => {
        setProduct(p)
        if (mySize && p.sizes.some((s) => s.size === mySize)) setSize(mySize) // Problem 9: start on my size
      })
      .catch((e: Error) => setError(e.message === 'Not found' ? "We couldn't find that product." : 'Could not load this product.'))
    window.scrollTo(0, 0)
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="container page"><p className="notice">{error}</p><Link to="/products">← Back to all products</Link></div>
  if (!product) return <div className="container page"><p className="muted">Loading…</p></div>

  const chosen = product.sizes.find((s) => s.size === size)

  return (
    <div className="container page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/products">Products</Link> / <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link> / <span>{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-img">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1 className="detail-name">{product.name}</h1>
          <div className="detail-price">{money(product.price)}</div>

          <p className="detail-desc">{product.description}</p>

          {product.colors.length > 0 && (
            <p className="detail-colors"><strong>Colors:</strong> {product.colors.join(', ')}</p>
          )}

          <div className="sizes">
            <div className="sizes-head">
              <strong>Size</strong>
              <span className="muted">{product.total_stock} in stock across all sizes</span>
            </div>
            <div className="size-grid">
              {product.sizes.map((s) => (
                <button
                  key={s.size}
                  className={`size size-${s.status} ${size === s.size ? 'selected' : ''}`}
                  onClick={() => setSize(s.size)}
                  aria-pressed={size === s.size}
                >
                  <span className="size-label">{s.size}</span>
                  <span className="size-qty">{s.quantity > 0 ? `${s.quantity} left` : 'Sold out'}</span>
                </button>
              ))}
            </div>
            {chosen && (
              <p className={`stock-note stock-${chosen.status}`}>
                {chosen.size}: {STATUS_LABEL[chosen.status]}
                {chosen.quantity > 0 && ` (${chosen.quantity} available)`}
              </p>
            )}
          </div>

          <table className="stock-table">
            <caption>Stock by size</caption>
            <thead><tr><th>Size</th><th>Quantity</th><th>Status</th></tr></thead>
            <tbody>
              {product.sizes.map((s) => (
                <tr key={s.size}><td>{s.size}</td><td>{s.quantity}</td><td className={`stock-${s.status}`}>{STATUS_LABEL[s.status]}</td></tr>
              ))}
            </tbody>
          </table>

          <Link to="/products" className="text-link">← Back to all products</Link>
        </div>
      </div>
    </div>
  )
}
