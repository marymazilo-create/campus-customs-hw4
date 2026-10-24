"""Campus Customs Shop: Pydantic / PydanticAI structured types (MGT 409 HW 4).

Three groups:
  1. Product shapes the website shows (cards and the detail page). main.py returns these.
  2. What the agent's tools hand back to the agent (tools.py).
  3. The chat: what the website sends, what the agent must answer with, and what the
     website gets back (agent reply + real product cards built from the database).
  4. Customer memory (Problem 8): page context, the customer the agent sees, saved history.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

MAX_PICKS = 6  # most product cards the chat puts on the page for one answer


# ---------- 1. products on the website ----------

class SizeStock(BaseModel):
    size: str
    quantity: int
    status: str  # "in_stock" | "low_stock" | "sold_out"


class ProductCard(BaseModel):
    """One product tile: on the Products page now, and under chat replies (Problem 7)."""
    product_id: str
    name: str
    garment_type: str
    category: str
    short_description: str
    price: float
    image_url: str
    in_stock: bool
    # Problem 9 "My size": filled in when the shopper has picked a size
    size: str | None = None
    size_quantity: int | None = None
    size_status: str | None = None


class ProductDetail(ProductCard):
    description: str
    colors: list[str]
    tags: list[str]
    sizes: list[SizeStock]
    total_stock: int


# ---------- 2. tool results (what the agent sees) ----------

class ProductHit(BaseModel):
    """A search match. Price and stock come from the lookup tools below, not from search."""
    product_id: str
    name: str
    category: str
    colors: list[str]
    short_description: str


class SizeHit(ProductHit):
    """find_in_size: a match that is in stock in the shopper's size (Problem 9)."""
    size: str
    quantity: int
    status: str  # "in_stock" | "low_stock"


class SimilarHit(ProductHit):
    """find_similar: a close alternative, with why it's similar (Problem 9)."""
    why_similar: list[str]
    size: str | None = None
    quantity: int | None = None
    status: str | None = None


class Audience(BaseModel):
    """A "Shop for" group on the website (Problem 9)."""
    key: str
    label: str
    blurb: str
    count: int
    image_url: str


class ProductInfo(BaseModel):
    """get_product_description: what the product is and looks like."""
    product_id: str
    name: str
    garment_type: str
    category: str
    description: str
    colors: list[str]


class PriceInfo(BaseModel):
    """get_price: the one real price from the catalogue."""
    product_id: str
    name: str
    price: float
    currency: str = "USD"


class StockInfo(BaseModel):
    """check_stock: how many are on hand, size by size.

    asked_size / asked_size_quantity / asked_size_status are filled in only when the
    shopper asked about one size, so the agent can answer that exact question.
    """
    product_id: str
    name: str
    sizes: list[SizeStock] = Field(description="Every size XS-XXL with its quantity and status")
    total_in_stock: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    asked_size: str | None = None
    asked_size_quantity: int | None = None
    asked_size_status: str | None = Field(None, description='"in_stock", "low_stock", "sold_out" or "not_offered"')


class StoreInfo(BaseModel):
    name: str
    address: str
    since: str
    website: str
    email: str
    phone: str
    returns: list[str]
    not_known: list[str] = Field(description="Things the bot must not guess about")


# ---------- 3. the chat ----------

class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message (Problem 8).

    Only the path and the product_id come from the browser. Everything the agent is
    told about that product is looked up in the database by the backend.
    """
    path: str = Field("/", max_length=200, description='e.g. "/products/basic-hoodie-big-yale" or "/products?category=Hoodies"')
    product_id: str | None = Field(None, max_length=120, description="Set when the shopper is on a single product page")


class GuestTurn(BaseModel):
    """One earlier message from a guest's open chat window (guests have no saved history)."""
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(max_length=2000)
    product_ids: list[str] = Field(default_factory=list, max_length=6,
                                   description="Cards that reply put on the page, so 'the second one' still works")


class ChatRequest(BaseModel):
    """What the chat widget sends to POST /api/chat. Who the shopper is comes from the
    login token in the Authorization header, never from this body."""
    message: str = Field(min_length=1, max_length=1000)
    page: PageContext = Field(default_factory=PageContext)
    guest_history: list[GuestTurn] = Field(default_factory=list, max_length=30,
                                           description="Ignored for logged-in shoppers (their history is in the database)")


class CustomerInfo(BaseModel):
    """The logged-in shopper, as the agent sees them. Never the password hash."""
    first_name: str
    last_name: str
    email: str


class PageProduct(BaseModel):
    """The product open on the page, looked up from the database for the agent."""
    product_id: str
    name: str
    category: str
    garment_type: str
    colors: list[str]
    price: float
    short_description: str
    image_url: str


class HistoryMessage(BaseModel):
    """One saved chat message, as the chat widget reloads it."""
    role: str  # "user" | "assistant"
    text: str
    product_count: int = 0
    results_title: str | None = None
    created_at: str


class AgentReply(BaseModel):
    """The agent's structured answer. The agent has to fill this in on every turn."""
    reply: str = Field(description="What Will says back to the shopper, in character. Plain text, 1-4 short sentences "
                                   "(a short list is fine when comparing products).")
    product_ids: list[str] = Field(default_factory=list, json_schema_extra={"maxItems": MAX_PICKS},
                                   description="Exact product_ids from tool results, most relevant first (at most 6). The website "
                                               "shows these as product cards on the page. Empty if no product fits "
                                               "or the message isn't about products.")
    results_title: str | None = Field(None, max_length=60,
                                      description="Short heading for the cards on the page, like 'Hoodies' or "
                                                  "'Yale Mom gear'. None when product_ids is empty.")

    @field_validator("product_ids", mode="before")
    @classmethod
    def keep_top_picks(cls, v):
        # More than 6? Keep the 6 most relevant instead of failing the whole answer.
        return list(v)[:MAX_PICKS] if isinstance(v, (list, tuple)) else v


class ChatResponse(BaseModel):
    """What POST /api/chat returns to the website (the chat -> page contract).

    reply          the words for the chat bubble
    results_title  heading for the "Will's picks" section on the page (None = leave the page alone)
    products       the product cards to show on the page, in the agent's order
    """
    reply: str
    results_title: str | None = None
    products: list[ProductCard] = Field(default_factory=list,
                                        description="Built from the database, never from the model's text, "
                                                    "so names, prices and photos are always real.")
