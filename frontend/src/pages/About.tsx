import { Link } from 'react-router-dom'

// DRAFT copy for Mary to review: written in our own words, inspired by yalebulldogblue.com.
export default function About() {
  return (
    <div className="container page narrow">
      <p className="eyebrow">About Us</p>
      <h1 className="page-title">A Broadway tradition since 1973</h1>
      <p className="lead">
        Campus Customs has been part of New Haven's Broadway shopping strip for more than fifty years.
        We carry officially licensed Yale apparel and gifts for everyone who calls Yale home, whether
        they're here for four years, a lifetime, or one big game.
      </p>

      <h2 className="sub-title">What we carry</h2>
      <ul className="about-list">
        <li><strong>Everyday Yale classics:</strong> hoodies, crewnecks, quarter-zips, tees and fleece jackets in Yale blue and heather gray.</li>
        <li><strong>Residential colleges:</strong> gear for Branford, Berkeley, Benjamin Franklin and the rest of the fourteen.</li>
        <li><strong>Teams:</strong> baseball, field hockey and more, plus The Game against Harvard.</li>
        <li><strong>Family lines:</strong> Yale Mom, Dad, Grandma and Grandpa, made for proud relatives.</li>
      </ul>

      <h2 className="sub-title">Shopping with us</h2>
      <p>
        Every price and stock count on this site comes straight from our inventory, and so does every
        answer from our chat assistant. If a size is sold out, we'll tell you.
      </p>
      <p>
        <strong>Returns:</strong> send items back within 30 days of shipping, unworn with tags attached.
        Custom-made and final-sale items can't be returned. Questions? Email orderdept@campuscustoms.com
        or call (475) 301-4205.
      </p>

      <div className="about-visit">
        <div>
          <h2 className="sub-title">Visit the shop</h2>
          <p>57 Broadway<br />New Haven, CT 06511</p>
        </div>
        <Link to="/products" className="btn btn-primary">Start shopping</Link>
      </div>
    </div>
  )
}
