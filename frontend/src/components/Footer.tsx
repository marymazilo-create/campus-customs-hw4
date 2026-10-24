import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div>
          <div className="footer-title">Campus Customs</div>
          <p>57 Broadway<br />New Haven, CT 06511</p>
        </div>
        <div>
          <div className="footer-title">Shop</div>
          <p><Link to="/products">All products</Link><br /><Link to="/products?category=Hoodies">Hoodies</Link><br /><Link to="/products?category=Crewnecks">Crewnecks</Link></p>
        </div>
        <div>
          <div className="footer-title">Help</div>
          <p>Returns within 30 days of shipping, unworn with tags.<br />orderdept@campuscustoms.com · (475) 301-4205</p>
        </div>
      </div>
      <div className="container footer-fine">© 2026 Campus Customs · Class project for MGT 409, not the official store.</div>
    </footer>
  )
}
