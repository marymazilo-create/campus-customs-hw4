"""Campus Customs Shop: tools the agent can call (MGT 409 HW 4).

Problem 5:
  search_products          find products by keywords (name, description, tags, type, colors)
  store_info               where the shop is and the returns policy
Problem 6 (lookups by exact product_id):
  get_product_description  catalogue: name, garment_type, description, colors
  get_price                catalogue: price
  check_stock              inventory: quantity for each size (or one size if asked)

Every tool only READS the database, and no tool can see the users / sessions tables
(no names, emails or password hashes).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from models import (Audience, PageProduct, PriceInfo, ProductHit, ProductInfo, SimilarHit, SizeHit, SizeStock, StockInfo,
                    StoreInfo)

ROOT = Path(__file__).resolve().parent.parent  # the hw4/ folder
DB_PATH = ROOT / "data" / "campus_customs.db"

# Words that show up in almost every product, so they don't help a search.
STOP = {"a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "me", "my", "i", "you", "do", "have",
        "got", "any", "some", "show", "find", "want", "need", "looking", "something", "yale", "campus",
        "customs", "merch", "gear", "please", "is", "are", "it", "that", "this", "what", "get"}

# Shoppers say "sweatshirt", the catalogue says "crewneck sweatshirt", and so on.
SYNONYMS = {
    "hoodies": "hoodie", "hooded": "hoodie", "hoody": "hoodie",
    "crew": "crewneck", "crewnecks": "crewneck", "sweatshirts": "sweatshirt",
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt", "shirt": "t-shirt", "shirts": "t-shirt",
    "quarterzip": "quarter-zip", "zip": "quarter-zip", "1/4": "quarter-zip",
    "jackets": "jacket", "mom": "mom", "mother": "mom", "dad": "dad", "father": "dad",
    "grandma": "grandma", "grandmother": "grandma", "grandpa": "grandpa", "grandfather": "grandpa",
    "grey": "gray", "blue": "navy",
}


CATEGORIES = ["Hoodies", "Crewnecks", "Tees & Tops", "Quarter-Zips", "Jackets", "Other"]
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 5  # at or below this, a size is "low_stock" (same rule as the product page)

# What shoppers type -> the size codes in the inventory table
SIZE_WORDS = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "extra extra large": "XXL", "2x": "XXL",
}


class ProductNotFound(ValueError):
    """No product with that id. The agent is told to search first and try again."""


def _connect() -> sqlite3.Connection:
    # Read-only connection: the agent can never change the database.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _category(garment_type: str) -> str:
    g = garment_type.lower()
    if "quarter-zip" in g or "1/4" in g:
        return "Quarter-Zips"
    if "jacket" in g or "fleece" in g:
        return "Jackets"
    if "hood" in g:
        return "Hoodies"
    if "crew" in g or "sweatshirt" in g:
        return "Crewnecks"
    if "t-shirt" in g or "shirt" in g:
        return "Tees & Tops"
    return "Other"


def _short(text: str, limit: int = 140) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def _terms(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9/'-]+", query.lower())
    return [SYNONYMS.get(w, w) for w in words if w not in STOP and len(w) > 1]


def search_products(query: str, category: str | None = None, limit: int = 8) -> list[ProductHit]:
    """Find products whose name, type, description, colors or tags match the shopper's words.

    Each word is scored (name and tags count most) so "navy hockey hoodie" ranks the
    Ice Hockey hoodie first. `category` (Hoodies, Crewnecks, Tees & Tops, Quarter-Zips,
    Jackets) limits results to one shop category; with a category, the query can be empty
    ("what hoodies do you have?"). An empty query with no category returns nothing.
    """
    limit = max(1, min(int(limit), 12))
    return [_hit(r) for r in _ranked(query, category)[:limit]]


def _hit(r: sqlite3.Row) -> ProductHit:
    return ProductHit(
        product_id=r["product_id"],
        name=r["name"],
        category=_category(r["garment_type"]),
        colors=json.loads(r["colors"] or "[]"),
        short_description=_short(r["description"]),
    )


def _ranked(query: str, category: str | None = None) -> list[sqlite3.Row]:
    """Every matching catalogue row, best match first (shared by the search tools)."""
    terms = _terms(query or "")
    cat = next((c for c in CATEGORIES if category and c.lower() == category.strip().lower()), None)
    if not terms and not cat:
        return []
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
    scored = []
    for r in rows:
        name, gtype = r["name"].lower(), r["garment_type"].lower()
        tags = " ".join(json.loads(r["search_tags"] or "[]")).lower()
        colors = " ".join(json.loads(r["colors"] or "[]")).lower()
        desc = r["description"].lower()
        if cat and _category(r["garment_type"]) != cat:
            continue
        score = 0 if terms else 1  # category only: every product in it matches
        for t in terms:
            score += 3 * (t in name) + 2 * (t in gtype) + 2 * (t in tags) + (t in colors) + (t in desc)
            if t == "sweatshirt" and "hood" in gtype:
                score -= 1  # "sweatshirt" usually means a crewneck, not a hoodie
        if score > 0:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [r for _, r in scored]


def store_info() -> StoreInfo:
    """The shop's basic facts. The agent may only quote these, never invent policies."""
    return StoreInfo(
        name="Campus Customs (Yale Bulldog Blue)",
        address="57 Broadway, New Haven, CT 06511",
        since="On Broadway since 1973",
        website="yalebulldogblue.com",
        email="orderdept@campuscustoms.com",
        phone="(475) 301-4205",
        returns=[
            "Returns within 30 days of the ship date.",
            "Items must be unworn with the tags still on.",
            "Custom and final-sale items can't be returned.",
            "Email your tracking number to orderdept@campuscustoms.com to start a return.",
            "The customer pays return shipping unless the shop made a mistake.",
            "Refunds don't include the original shipping and take 2-10 business days.",
        ],
        not_known=["store hours", "shipping times and costs", "current sales or discount codes",
                   "custom or bulk orders"],
    )


# ---------- Problem 6: lookups by exact product_id ----------

def stock_status(qty: int) -> str:
    if qty <= 0:
        return "sold_out"
    if qty <= LOW_STOCK:
        return "low_stock"
    return "in_stock"


def normalize_size(size: str) -> str:
    """'medium' -> 'M', '2XL' -> 'XXL'. Returns the cleaned text if it isn't a size we know."""
    key = size.strip().lower().replace("size", "").strip()
    return SIZE_WORDS.get(key, size.strip().upper())


def _catalogue_row(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()
    if row is None:
        raise ProductNotFound(f"No product with product_id {product_id!r}. Use search_products to find the exact id.")
    return row


def get_product_description(product_id: str) -> ProductInfo:
    """The product's full description, type and colors, straight from the catalogue."""
    with _connect() as conn:
        r = _catalogue_row(conn, product_id)
    return ProductInfo(
        product_id=r["product_id"],
        name=r["name"],
        garment_type=r["garment_type"],
        category=_category(r["garment_type"]),
        description=r["description"],
        colors=json.loads(r["colors"] or "[]"),
    )


def get_price(product_id: str) -> PriceInfo:
    """The real price from the catalogue."""
    with _connect() as conn:
        r = _catalogue_row(conn, product_id)
    return PriceInfo(product_id=r["product_id"], name=r["name"], price=float(r["price"]))


def check_stock(product_id: str, size: str | None = None) -> StockInfo:
    """Quantity on hand for every size; if a size is given, that size's answer is filled in too."""
    with _connect() as conn:
        r = _catalogue_row(conn, product_id)
        inv = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (r["product_id"],)).fetchall()
    order = {s: i for i, s in enumerate(SIZE_ORDER)}
    sizes = sorted(
        (SizeStock(size=i["size"], quantity=i["quantity"], status=stock_status(i["quantity"])) for i in inv),
        key=lambda s: order.get(s.size, 99),
    )
    info = StockInfo(
        product_id=r["product_id"],
        name=r["name"],
        sizes=sizes,
        total_in_stock=sum(s.quantity for s in sizes),
        sizes_in_stock=[s.size for s in sizes if s.quantity > 0],
        sizes_sold_out=[s.size for s in sizes if s.quantity <= 0],
    )
    if size:
        asked = normalize_size(size)
        match = next((s for s in sizes if s.size == asked), None)
        info.asked_size = asked
        info.asked_size_quantity = match.quantity if match else 0
        info.asked_size_status = match.status if match else "not_offered"
    return info


# ---------- Problem 8: the product open on the page ----------

def page_product(product_id: str | None) -> PageProduct | None:
    """The product the shopper is looking at, from the database (None if there isn't one)."""
    if not product_id:
        return None
    with _connect() as conn:
        r = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id.strip(),)).fetchone()
    if r is None:
        return None
    return PageProduct(
        product_id=r["product_id"],
        name=r["name"],
        category=_category(r["garment_type"]),
        garment_type=r["garment_type"],
        colors=json.loads(r["colors"] or "[]"),
        price=float(r["price"]),
        short_description=_short(r["description"]),
        image_url="/images/" + Path(r["image_file_path"]).name,
    )


# ---------- Problem 9: usability improvements ----------

# Agent improvement 1: size-aware search ------------------------------------

def _size_qty(conn: sqlite3.Connection, size: str) -> dict[str, int]:
    return {r["product_id"]: r["quantity"] for r in
            conn.execute("SELECT product_id, quantity FROM inventory WHERE size = ?", (size,)).fetchall()}


def find_in_size(size: str, query: str = "", category: str | None = None, limit: int = 6) -> list[SizeHit]:
    """Products matching the shopper's words/category that are IN STOCK in one size, in one call.

    Replaces search + a check_stock call per product ("hoodies in medium" used to take
    up to 7 tool calls; now it's 1), and never suggests something sold out in their size.
    """
    code = normalize_size(size)
    if code not in SIZE_ORDER:
        return []
    limit = max(1, min(int(limit), 12))
    rows = _ranked(query, category)
    with _connect() as conn:
        qty = _size_qty(conn, code)
    hits = []
    for r in rows:
        q = qty.get(r["product_id"], 0)
        if q > 0:
            h = _hit(r)
            hits.append(SizeHit(**h.model_dump(), size=code, quantity=q, status=stock_status(q)))
        if len(hits) >= limit:
            break
    return hits


# Agent improvement 2: find similar items ------------------------------------

GENERIC_TAGS = {"yale", "yale university", "college apparel", "campus customs", "yale merch", "college merch",
                "university merch", "campus merch", "campus apparel", "long sleeve", "short sleeve", "pullover",
                "sweatshirt", "ivy league", "collegiate apparel", "university merchandise"}


def _tagset(r: sqlite3.Row) -> set[str]:
    return {t.strip().lower() for t in json.loads(r["search_tags"] or "[]")} - GENERIC_TAGS


# Shoppers and the catalogue spell colors differently ("grey" vs "gray", "blue" vs "navy").
COLOR_ALIASES = {
    "grey": ["gray", "grey", "charcoal"], "gray": ["gray", "grey", "charcoal"], "charcoal": ["charcoal"],
    "blue": ["blue", "navy"], "navy": ["navy"], "white": ["white", "ivory", "cream"],
    "cream": ["cream", "ivory", "off-white"], "ivory": ["ivory", "cream"], "red": ["red", "crimson", "maroon"],
    "black": ["black"], "green": ["green", "olive"], "pink": ["pink", "coral"], "coral": ["coral"],
}


def color_words(color: str | None) -> list[str]:
    """The catalogue spellings to look for when a shopper names a color."""
    c = (color or "").strip().lower()
    if not c:
        return []
    return COLOR_ALIASES.get(c, [c])


NAME_FILLER = {"yale", "hoodie", "hood", "crewneck", "crew", "t", "shirt", "zip", "1", "4", "jacket", "the", "of",
               "and", "university", "college", "logo"}


def _name_words(r: sqlite3.Row) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", r["name"].lower())) - NAME_FILLER


def find_similar(product_id: str, color: str | None = None, size: str | None = None, limit: int = 4) -> list[SimilarHit]:
    """Close alternatives to one product: same kind of item, shared themes (sport, college,
    family line, design), optionally in a wanted color and/or in stock in a size.

    For when the shopper's pick is sold out in their size or doesn't come in their color.
    """
    limit = max(1, min(int(limit), 6))
    code = normalize_size(size) if size else None
    if code and code not in SIZE_ORDER:
        code = None
    wanted = color_words(color)
    with _connect() as conn:
        base = _catalogue_row(conn, product_id)
        rows = conn.execute("SELECT * FROM catalogue WHERE product_id != ?", (base["product_id"],)).fetchall()
        qty = _size_qty(conn, code) if code else {}
    base_cat, base_tags = _category(base["garment_type"]), _tagset(base)
    base_words, base_colors = _name_words(base), [c.lower() for c in json.loads(base["colors"] or "[]")]
    scored = []
    for r in rows:
        colors = [c.lower() for c in json.loads(r["colors"] or "[]")]
        if wanted and not any(w in c for w in wanted for c in colors):
            continue  # they asked for a color: only items that come in it
        if code and qty.get(r["product_id"], 0) <= 0:
            continue  # they need a size: only items in stock in it
        shared = sorted(base_tags & _tagset(r))
        same_cat = _category(r["garment_type"]) == base_cat
        same_line = base_words & _name_words(r)  # e.g. both "Left Chest" or both "Tri Blend Sports"
        same_colors = set(base_colors) & set(colors)
        score = 3 * same_cat + 2 * len(same_line) + len(shared) + 0.5 * len(same_colors)
        if score == 0:
            continue
        reasons = ((["same type (" + base_cat + ")"] if same_cat else [])
                   + (["same line: " + " ".join(w for w in re.findall(r"[a-z0-9]+", base["name"].lower()) if w in same_line)]
                      if same_line else []) + shared[:2])
        q = qty.get(r["product_id"]) if code else None
        scored.append((score, r, reasons, q))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [
        SimilarHit(**_hit(r).model_dump(), why_similar=reasons,
                   size=code, quantity=q, status=stock_status(q) if q is not None else None)
        for _, r, reasons, q in scored[:limit]
    ]


# Front-end improvement 2: shop by who it's for -----------------------------
# Matched on the product_id, which spells out the line ("yale-mom-hoodie", "branford-1-4-zip").

AUDIENCES: list[dict] = [
    {"key": "mom", "label": "For Mom", "blurb": "Yale Mom hoodies and crewnecks",
     "match": ["yale-mom"]},
    {"key": "dad", "label": "For Dad", "blurb": "Yale Dad hoodies, crews and tees",
     "match": ["yale-dad"]},
    {"key": "grandparents", "label": "For Grandparents", "blurb": "Yale Grandma and Grandpa",
     "match": ["grandma", "grandpa"]},
    {"key": "family", "label": "For the Family", "blurb": "Aunt, Uncle, Brother, Cousin",
     "match": ["yale-aunt", "yale-uncle", "yale-brother", "yale-cousin"]},
    {"key": "colleges", "label": "Residential Colleges", "blurb": "Rep your college: Branford to Trumbull",
     "match": ["branford", "berkeley", "benjamin-franklin", "davenport", "grace-hopper", "jonathan-edwards",
               "morse", "pierson", "saybrook", "timothy-dwight", "trumbull", "silliman", "ezra-stiles", "pauli-murray"]},
    {"key": "grad", "label": "Grad & Professional Schools", "blurb": "SOM, Law, Medicine, Nursing and more",
     "match": ["school-of-", "law-school", "divinity-school", "forest-school"]},
    {"key": "athletes", "label": "Athletes & Fans", "blurb": "Hockey, football, crew, squash and more",
     "match": ["baseball", "basketball", "football", "hockey", "soccer", "tennis", "golf", "volleyball", "diving",
               "swimming", "fencing", "sailing", "squash", "lacrosse", "track", "crew-left-chest", "harvard"]},
]


def audience_of(key: str | None) -> dict | None:
    return next((a for a in AUDIENCES if key and a["key"] == key.strip().lower()), None)


def in_audience(product_id: str, audience: dict) -> bool:
    return any(m in product_id for m in audience["match"])


def audiences() -> list[Audience]:
    with _connect() as conn:
        ids = [r["product_id"] for r in conn.execute("SELECT product_id FROM catalogue ORDER BY name").fetchall()]
    out = []
    for a in AUDIENCES:
        members = [i for i in ids if in_audience(i, a)]
        if members:
            out.append(Audience(key=a["key"], label=a["label"], blurb=a["blurb"], count=len(members),
                                image_url=f"/images/{members[0]}.jpg"))
    return out
