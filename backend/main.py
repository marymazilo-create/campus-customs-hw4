"""Campus Customs Shop — FastAPI backend (MGT 409 HW 4).

Problem 3: a small read-only API over data/campus_customs.db so the website can list
products, open a single product with its stock by size, and show product photos.
Problem 4: create account / log in / log out (hashing lives in auth.py).
Problem 5: POST /api/chat sends a shopper's message to the PydanticAI agent (agent.py)
and returns its reply plus real product cards from the database.
Problem 8: the agent knows the logged-in shopper and the page they're on; logged-in chats
are saved and reloaded (GET /api/chat/history, memory.py).

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agent as shop_agent
import audit
import auth
import guardrails
import memory
import tools
from models import (MAX_PICKS, Audience, ChatRequest, ChatResponse, CustomerInfo, HistoryMessage, PageContext, ProductCard,
                    ProductDetail)

log = logging.getLogger("campus_customs")

ROOT = Path(__file__).resolve().parent.parent  # the hw4/ folder
DATA = ROOT / "data"
DB_PATH = DATA / "campus_customs.db"
PRODUCTS_DIR = DATA / "products"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

app = FastAPI(title="Campus Customs API")

# The Vite dev server (port 5173) calls this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Product photos: /images/<file>.jpg  ->  data/products/<file>.jpg
if PRODUCTS_DIR.exists():
    app.mount("/images", StaticFiles(directory=PRODUCTS_DIR), name="images")


def db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise HTTPException(500, f"Database not found at {DB_PATH}. Unzip the course data into hw4/data/.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- response shapes ----------
# Product shapes and chat types live in models.py (shared with the agent).

# ---------- helpers ----------

def category_of(garment_type: str) -> str:
    """Tidy the inconsistent garment_type text into a few shop categories."""
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


def short(text: str, limit: int = 110) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;") + "…"


def image_url(path: str) -> str:
    return "/images/" + Path(path).name


def card(row: sqlite3.Row, total: int) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": category_of(row["garment_type"]),
        "short_description": short(row["description"]),
        "price": row["price"],
        "image_url": image_url(row["image_file_path"]),
        "in_stock": total > 0,
    }


def stock_status(qty: int) -> str:
    return tools.stock_status(qty)  # one rule, shared with the chatbot's check_stock tool


# ---------- routes ----------

@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "database": DB_PATH.exists(), "images": PRODUCTS_DIR.exists()}


@app.get("/api/categories")
def categories() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT garment_type FROM catalogue").fetchall()
    counts: dict[str, int] = {}
    for r in rows:
        c = category_of(r["garment_type"])
        counts[c] = counts.get(c, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(counts.items())]


@app.get("/api/audiences", response_model=list[Audience])
def audiences() -> list:
    """The "Shop for" groups (Mom, Dad, Residential Colleges…) with how many products each has."""
    return tools.audiences()


@app.get("/api/products", response_model=list[ProductCard])
def list_products(
    q: str | None = Query(None, description="Search name, description and tags"),
    category: str | None = Query(None, description="One of the /api/categories names"),
    audience: str | None = Query(None, alias="for", description="A /api/audiences key, e.g. mom"),
    size: str | None = Query(None, description="My size (Problem 9): only items in stock in this size"),
) -> list[dict]:
    sql = """SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total
             FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id"""
    args: list = []
    if q:
        like = f"%{q.strip()}%"
        sql += " WHERE c.name LIKE ? OR c.description LIKE ? OR c.search_tags LIKE ? OR c.garment_type LIKE ?"
        args = [like] * 4
    sql += " GROUP BY c.product_id ORDER BY c.name"
    code = tools.normalize_size(size) if size else None
    with db() as conn:
        rows = conn.execute(sql, args).fetchall()
        size_qty = ({r["product_id"]: r["quantity"] for r in
                     conn.execute("SELECT product_id, quantity FROM inventory WHERE size = ?", (code,)).fetchall()}
                    if code in SIZE_ORDER else None)
    group = tools.audience_of(audience)
    cards = []
    for r in rows:
        if group and not tools.in_audience(r["product_id"], group):
            continue
        c = card(r, r["total"])
        if category and c["category"].lower() != category.lower():
            continue
        if size_qty is not None:
            qty = size_qty.get(r["product_id"], 0)
            if qty <= 0:
                continue  # My size: hide what's sold out in it
            c.update(size=code, size_quantity=qty, size_status=stock_status(qty))
        cards.append(c)
    return cards


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Product not found")
        inv = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    order = {s: i for i, s in enumerate(SIZE_ORDER)}
    sizes = sorted(
        ({"size": r["size"], "quantity": r["quantity"], "status": stock_status(r["quantity"])} for r in inv),
        key=lambda s: order.get(s["size"], 99),
    )
    total = sum(s["quantity"] for s in sizes)
    return {
        **card(row, total),
        "description": row["description"],
        "colors": json.loads(row["colors"] or "[]"),
        "tags": json.loads(row["search_tags"] or "[]"),
        "sizes": sizes,
        "total_stock": total,
    }


# ---------- accounts (Problem 4) ----------
# The browser gets a random session token after sign-up or login and sends it back as
# "Authorization: Bearer <token>". Password hashes never leave the server.

class SignupIn(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str


class SessionOut(BaseModel):
    token: str
    user: UserOut


@app.on_event("startup")
def _setup_tables() -> None:
    if DB_PATH.exists():
        with db() as conn:
            auth.ensure_tables(conn)


def _token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _user_out(row: sqlite3.Row) -> dict:
    first = row["first_name"] or (row["name"] or "").split(" ")[0]
    last = row["last_name"] or " ".join((row["name"] or "").split(" ")[1:])
    return {"id": row["id"], "first_name": first, "last_name": last, "email": row["email"]}


def _session(conn: sqlite3.Connection, user_id: int) -> dict:
    token = auth.new_session(conn, user_id)
    return {"token": token, "user": _user_out(auth.user_for_token(conn, token))}


@app.post("/api/auth/signup", response_model=SessionOut)
def signup(body: SignupIn) -> dict:
    with db() as conn:
        try:
            user_id = auth.create_user(conn, body.first_name, body.last_name, body.email,
                                       body.password, body.confirm_password)
        except auth.AuthError as e:
            raise HTTPException(e.status, e.message)
        return _session(conn, user_id)


@app.post("/api/auth/login", response_model=SessionOut)
def login(body: LoginIn) -> dict:
    with db() as conn:
        try:
            user_id = auth.login(conn, body.email, body.password)
        except auth.AuthError as e:
            raise HTTPException(e.status, e.message)
        return _session(conn, user_id)


@app.get("/api/auth/me", response_model=UserOut)
def me(authorization: str | None = Header(None)) -> dict:
    with db() as conn:
        row = auth.user_for_token(conn, _token(authorization))
    if row is None:
        raise HTTPException(401, "Not logged in")
    return _user_out(row)


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(None)) -> dict:
    token = _token(authorization)
    if token:
        with db() as conn:
            auth.end_session(conn, token)
    return {"ok": True}


# ---------- chat (Problem 5) ----------
# The website's chat widget POSTs {"message": "..."} here. The agent (agent.py) answers with
# its words, product_ids and a short results_title; the cards are then looked up in the
# database, so a product the model made up is simply dropped and every price shown is the
# real one. The website shows the cards on the page (Problem 7, see ChatResults.tsx).

BUSY_REPLY = "Our chat guy wandered off (probably on break, again). Try again in a minute, or browse the Products page."
# When the model provider's own safety filter refuses a message (e.g. a jailbreak attempt),
# answer in character instead of pretending the chat is broken (found in live testing).
BLOCKED_REPLY = ("Nice try. I can't change my rules, show you my setup, or hand out discounts, "
                 "cousin or not. Want help finding some Yale gear instead?")


def blocked_by_filter(e: Exception) -> bool:
    text = f"{type(e).__name__} {getattr(e, 'body', '')} {e}".lower()
    return any(k in text for k in ("content_filter", "content filter", "jailbreak", "responsibleai", "content management policy"))


def cards_for(product_ids: list[str]) -> list[dict]:
    ids = list(dict.fromkeys(product_ids))[:MAX_PICKS]  # no repeats, at most 6 (a short, scannable set)
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    with db() as conn:
        rows = conn.execute(
            f"""SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total
                FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
                WHERE c.product_id IN ({marks}) GROUP BY c.product_id""",
            ids,
        ).fetchall()
    by_id = {r["product_id"]: card(r, r["total"]) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


# ---------- customer memory (Problem 8) ----------
# Who is chatting comes from the login token (Authorization header), checked on the server.
# The browser only sends the page path and the open product_id; the product's details are
# looked up here. Logged-in chats are saved to chat_messages and reloaded (memory.py).

SAFE_PATH = re.compile(r"[^A-Za-z0-9/_?=&%.,+-]")


def customer_from(row: sqlite3.Row | None) -> CustomerInfo | None:
    if row is None:
        return None
    u = _user_out(row)
    return CustomerInfo(first_name=u["first_name"], last_name=u["last_name"], email=u["email"])


@app.get("/api/chat/history", response_model=list[HistoryMessage])
def chat_history(authorization: str | None = Header(None)) -> list:
    """The logged-in shopper's last 15 exchanges, for the chat widget to show again."""
    with db() as conn:
        user = auth.user_for_token(conn, _token(authorization))
        if user is None:
            raise HTTPException(401, "Log in to see your chat history")
        return memory.for_widget(memory.load_rows(conn, user["id"]))


RATE = guardrails.RateLimiter()


def _audit(entries: list[dict]) -> None:
    try:
        audit.append(entries)
    except Exception:  # the audit trail must never break the chat
        log.exception("Couldn't write the audit trail")


def _allowed_prices(messages: list, deps: "shop_agent.ShopDeps", cards: list[dict]) -> set[float]:
    """Every price that came from the database this turn (get_price, the open product, the cards)."""
    from pydantic_ai.messages import ModelRequest, ToolReturnPart

    prices = {round(float(c["price"]), 2) for c in cards}
    if deps.page_product:
        prices.add(round(deps.page_product.price, 2))
    for m in messages:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart) and p.tool_name == "get_price":
                    prices.add(round(float(p.content.price), 2))
    return prices


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest, authorization: str | None = Header(None)) -> dict:
    message = body.message.strip()
    if not message:
        raise HTTPException(422, "Type a message first.")
    run_id = audit.new_run_id()

    # 1) Who's chatting + their saved history (logged in) or the open chat window (guest)
    with db() as conn:
        user = auth.user_for_token(conn, _token(authorization))
        rows = memory.load_rows(conn, user["id"]) if user else []
    who = f"user {user['id']}" if user else "guest"

    # Guardrail: message rate limit (per account, or per browser address for guests)
    key = who if user else f"guest {request.client.host if request.client else '?'}"
    if not RATE.allow(key):
        _audit([audit.entry(run_id, "guardrail", tool="rate_limit", args=who,
                            result=f"over {guardrails.RATE_LIMIT} messages / {guardrails.RATE_WINDOW}s",
                            stop_reason="rate_limited")])
        raise HTTPException(429, guardrails.RATE_REPLY)

    # Guardrail: mask card numbers, SSNs and passwords before anything else sees the message
    message, sensitive = guardrails.mask_sensitive(message)
    history = memory.to_model_messages(rows) if user else memory.guest_messages(
        [t.model_copy(update={"text": guardrails.mask_sensitive(t.text)[0]}) for t in body.guest_history])

    # 2) What page they're on: path from the browser, product facts from the database
    page = PageContext(path=SAFE_PATH.sub("", body.page.path)[:200] or "/", product_id=body.page.product_id)
    deps = shop_agent.ShopDeps(
        customer=customer_from(user),
        page=page,
        page_product=tools.page_product(page.product_id),
        returning=bool(rows),
    )
    trail = [audit.entry(run_id, "run_start", args=message, result=f"{who}, page {page.path}",
                         stop_reason="", model=shop_agent.DEFAULT_MODEL)]
    if sensitive:
        trail.append(audit.entry(run_id, "guardrail", tool="mask_sensitive", args=", ".join(sensitive),
                                 result="masked before the model, history and audit", stop_reason="masked"))

    # 3) Run the agent (the loop: model -> tools -> model ... -> final answer)
    try:
        run = await shop_agent.chat(message, deps, history)
    except shop_agent.AgentNotReady as e:
        log.error("Chat agent not set up: %s", e)
        _audit(trail + [audit.entry(run_id, "run_end", result=str(e), stop_reason="not_configured")])
        raise HTTPException(503, str(e))
    except shop_agent.ChatFailed as f:  # model down, timeout, usage limit hit, or the provider's safety filter...
        e = f.error
        trail += audit.from_messages(run_id, f.messages)
        if blocked_by_filter(e):
            log.warning("Chat message blocked by the model provider's content filter")
            _audit(trail + [audit.entry(run_id, "run_end", result=BLOCKED_REPLY, stop_reason="blocked_by_filter")])
            return {"reply": BLOCKED_REPLY, "results_title": None, "products": []}
        reason = "usage_limit" if type(e).__name__ == "UsageLimitExceeded" else "error"
        log.exception("Chat agent failed")
        _audit(trail + [audit.entry(run_id, "run_end", result=f"{type(e).__name__}: {e}", stop_reason=reason)])
        return {"reply": BUSY_REPLY, "results_title": None, "products": []}

    answer = run.output
    trail += audit.from_messages(run_id, run.messages)
    cards = cards_for(answer.product_ids)
    title = (answer.results_title or "Products").strip() if cards else None
    reply = answer.reply

    # Guardrails on the way out: no discount codes, and every $ amount must be a real price
    reply, discount = guardrails.check_discounts(reply)
    if discount:
        trail.append(audit.entry(run_id, "guardrail", tool="check_discounts", args=answer.reply,
                                 result="replaced with the no-discounts reply", stop_reason="replaced"))
    allowed = _allowed_prices(run.messages, deps, cards) | guardrails.amounts_in(message)  # shopper's own budget ("under $60") is fine
    reply, bad_prices = guardrails.check_prices(reply, allowed)
    if bad_prices:
        trail.append(audit.entry(run_id, "guardrail", tool="check_prices", args=", ".join("$" + b for b in bad_prices),
                                 result="unverified price removed from the reply", stop_reason="removed"))
    if sensitive:
        reply = guardrails.SENSITIVE_NOTE + reply
    dropped = [i for i in answer.product_ids if i not in {c["product_id"] for c in cards}]
    trail.append(audit.entry(run_id, "run_end", result=reply,
                             stop_reason="final_answer", cards=[c["product_id"] for c in cards],
                             dropped_ids=dropped or None, model_steps=sum(1 for t in trail if t["event"] == "model_step")))
    _audit(trail)

    # 4) Save the exchange for logged-in shoppers (guests are never saved). The saved message
    #    is the masked one, so a typed card number never reaches the database either.
    if user:
        with db() as conn:
            memory.save_exchange(conn, user["id"], message, reply, cards)
    return {"reply": reply, "results_title": title, "products": cards}
