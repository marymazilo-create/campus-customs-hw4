import { Link } from 'react-router-dom'
import { money, type ProductCard as Card } from '../api'

// The whole card is a link, so clicking anywhere on it opens the product page.
export default function ProductCard({ product }: { product: Card }) {
  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {!product.in_stock && <span className="badge badge-out">Sold out</span>}
      </div>
      <div className="card-body">
        <div className="card-cat">{product.category}</div>
        <h3 className="card-name">{product.name}</h3>
        <p className="card-desc">{product.short_description}</p>
        <div className="card-foot">
          <span className="card-price">{money(product.price)}</span>
          {product.size && product.size_status && (
            <span className={`size-tag stock-${product.size_status}`}>
              {product.size}: {product.size_status === 'low_stock' ? `only ${product.size_quantity} left` : 'in stock'}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
