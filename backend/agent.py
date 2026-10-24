"""Campus Customs Shop: the chatbot agent (MGT 409 HW 4).

How the agent is loaded:
  1. Key and model: PORTKEY_API_KEY and MODEL_NAME come from .env (hw4/.env if there is
     one, otherwise the shared emba/.env). Calls go through Portkey, same as Homeworks 2-3.
  2. Instructions: prompts/prompt.md is read fresh on every message, so edits to the
     prompt show up on the next chat message without restarting the server.
  3. Tools: the functions in tools.py, registered below with @agent.tool.
  4. Output: the agent must answer with an AgentReply (models.py): its words + product_ids.
  5. Context (Problem 8): ShopDeps carries who is chatting and what page they're on. A second
     instructions function turns it into a short "Right now" note the agent reads every turn,
     and earlier messages arrive as PydanticAI message_history (memory.py).

main.py calls `await chat(message, deps, history)`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # quiet PydanticAI's startup banner in the Terminal

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelRetry, NativeOutput, RunContext, capture_run_messages
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import tools
from models import (AgentReply, CustomerInfo, PageContext, PageProduct, PriceInfo, ProductHit, ProductInfo, SimilarHit,
                    SizeHit, StockInfo, StoreInfo)
from pydantic_ai.messages import ModelMessage

BACKEND = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND / "prompts" / "prompt.md"
HW4 = BACKEND.parent

# hw4/.env first; then the shared one at the top of the class folder (emba/.env).
# load_dotenv never overwrites a value that's already set, so the first file wins.
load_dotenv(HW4 / ".env")
load_dotenv(HW4.parent.parent / ".env")

PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
DEFAULT_MODEL = "gpt-5.6-luna"  # the course "brain" model; gpt-6-astra rejects tool calls on Portkey (HW3)
ALLOWED_MODELS = ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol")
LIMITS = UsageLimits(request_limit=6)  # at most 6 model calls per shopper message (cost + loop guard)


class AgentNotReady(RuntimeError):
    """The key or model setting is missing or wrong."""


@dataclass
class ShopDeps:
    """Per-message context handed to the agent and every tool (Problem 8).

    customer      the logged-in shopper (from their login token on the server), or None for a guest
    page          the path the shopper is on, sent by the browser
    page_product  the product open on that page, looked up in the database by the backend
    returning     True when a logged-in shopper has saved chat history
    """
    customer: CustomerInfo | None = None
    page: PageContext = field(default_factory=PageContext)
    page_product: PageProduct | None = None
    returning: bool = False


def context_note(deps: ShopDeps) -> str:
    """The "Right now" note added to the instructions on every message."""
    lines = ["## Right now", "", "### Who you're talking to"]
    c = deps.customer
    if c:
        lines += [
            f"- Logged in. First name: {c.first_name}. Last name: {c.last_name}. Email: {c.email} (private: only say it if they ask what email they're logged in with).",
            f"- {'Returning shopper: your earlier chats with them are in the conversation above.' if deps.returning else 'First chat with them.'}",
        ]
    else:
        lines.append("- A guest (not logged in). You don't know their name. Don't ask for it or their email. "
                     "If it helps, mention that logging in lets you remember their chats.")
    lines += ["", "### What page they're on", f"- Page: {deps.page.path or '/'}"]
    p = deps.page_product
    if p:
        lines += [
            f"- They're looking at **{p.name}** (product_id `{p.product_id}`): {p.category}, {p.garment_type}, "
            f"colors: {', '.join(p.colors) or 'not listed'}, ${p.price:.2f}. {p.short_description}",
            '- "This", "these", "it", "this one", "that" and "those" mean this product, even if earlier replies showed other '
            'products, unless they clearly mean another one (e.g. "the ones you showed me"). '
            "Use this product_id for get_price, check_stock and get_product_description, and include it in product_ids.",
        ]
    else:
        lines.append("- Not on a single product page. If they say \"this\" with no product in the conversation, ask which one.")
    return "\n".join(lines)


def model_name() -> str:
    name = (os.getenv("MODEL_NAME") or DEFAULT_MODEL).strip()
    if name not in ALLOWED_MODELS:
        raise AgentNotReady(f"MODEL_NAME={name!r} isn't a course chat model. Use one of {', '.join(ALLOWED_MODELS)}.")
    return name


def build_model() -> OpenAIChatModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise AgentNotReady("PORTKEY_API_KEY is missing. Put it in hw4/.env (see .env.example) or emba/.env.")
    base_url = (os.getenv("OPENAI_BASE_URL") or PORTKEY_BASE_URL).rstrip("/")
    return OpenAIChatModel(model_name(), provider=OpenAIProvider(base_url=base_url, api_key=api_key))


def read_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_agent() -> Agent[ShopDeps, AgentReply]:
    """Build the agent once (on the first chat message) and reuse it."""
    agent = Agent(
        build_model(),
        deps_type=ShopDeps,
        output_type=NativeOutput(AgentReply),  # JSON-schema output: worked with Portkey in HW3
        retries=2,
    )

    @agent.instructions
    def system_prompt() -> str:
        return read_prompt()

    @agent.instructions
    def right_now(ctx: RunContext[ShopDeps]) -> str:
        return context_note(ctx.deps)

    @agent.tool
    def search_products(ctx: RunContext[ShopDeps], query: str, category: str | None = None,
                        limit: int = 8) -> list[ProductHit]:
        """Search the Campus Customs catalogue by the shopper's words (type, sport, college, color, school,
        family line like "Yale Mom"). Optional `category`: one of Hoodies, Crewnecks, Tees & Tops,
        Quarter-Zips, Jackets, to get everything of that type ("what hoodies do you have?"); the query can
        then be empty or narrow it ("hockey"). `limit` up to 12. Returns product_id, name, category, colors
        and a short description. Call this before recommending anything, and to get the exact product_id for
        the lookups below. Search results have NO price or stock: use get_price / check_stock for those."""
        return tools.search_products(query, category, limit)

    @agent.tool
    def get_product_description(ctx: RunContext[ShopDeps], product_id: str) -> ProductInfo:
        """Full description, garment type and colors for one product (exact product_id from search).
        Use for "what does it look like / what color / what is it made like" questions."""
        try:
            return tools.get_product_description(product_id)
        except tools.ProductNotFound as e:
            raise ModelRetry(str(e))

    @agent.tool
    def get_price(ctx: RunContext[ShopDeps], product_id: str) -> PriceInfo:
        """The real price of one product (exact product_id from search). Call this before saying any price."""
        try:
            return tools.get_price(product_id)
        except tools.ProductNotFound as e:
            raise ModelRetry(str(e))

    @agent.tool
    def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str | None = None) -> StockInfo:
        """How many are on hand for one product, size by size (XS, S, M, L, XL, XXL).
        Pass `size` when the shopper asks about one size ("medium", "XL", "2XL" all work); the answer is in
        asked_size_quantity and asked_size_status ("in_stock", "low_stock", "sold_out", "not_offered").
        Call this before saying anything is in stock or sold out."""
        try:
            return tools.check_stock(product_id, size)
        except tools.ProductNotFound as e:
            raise ModelRetry(str(e))

    @agent.tool
    def find_in_size(ctx: RunContext[ShopDeps], size: str, query: str = "", category: str | None = None,
                     limit: int = 6) -> list[SizeHit]:
        """Products that are IN STOCK in one size, in one call (Problem 9). Use whenever the shopper names a
        size while looking for something: "hoodies in medium", "any XL crewnecks?", "Yale Mom stuff in a small".
        `size`: XS, S, M, L, XL, XXL (or words like "medium", "2XL"). `query` and/or `category` work like
        search_products. Each result has the size's quantity and status, so no check_stock calls are needed."""
        return tools.find_in_size(size, query, category, limit)

    @agent.tool
    def find_similar(ctx: RunContext[ShopDeps], product_id: str, color: str | None = None, size: str | None = None,
                     limit: int = 4) -> list[SimilarHit]:
        """Close alternatives to one product (Problem 9): same kind of item and shared themes (sport, college,
        family line, design), with `why_similar`. Use when their pick is sold out in their size (pass `size`),
        doesn't come in the color they want (pass `color`), or they ask for "something like this"."""
        try:
            return tools.find_similar(product_id, color, size, limit)
        except tools.ProductNotFound as e:
            raise ModelRetry(str(e))

    @agent.tool
    def store_info(ctx: RunContext[ShopDeps]) -> StoreInfo:
        """The shop's address, contact info and returns policy, plus the things you must NOT guess about."""
        return tools.store_info()

    return agent


def with_page_note(message: str, deps: ShopDeps) -> str:
    """On a product page, pin the open product right next to the question.

    Live testing showed long chat histories can outweigh the "Right now" note in the
    instructions: a logged-in shopper on the Basic Hoodie page asked "how many of these in
    medium?" and Will answered about the Yale Dad picks from an earlier reply. A short tag in
    the message itself (where the model looks hardest) fixes that. Only this turn sees it;
    the saved history keeps the shopper's own words.
    """
    p = deps.page_product
    if not p:
        return message
    return (f"[Page: the shopper is looking at {p.name} (product_id {p.product_id}). "
            f'"This", "these", "it" and "that" mean this product unless they clearly say otherwise.]\n{message}')


@dataclass
class ChatRun:
    """What one agent run produced: the answer, plus every message of the loop (for the audit
    trail and the price check). `messages` is filled in even when the run fails."""
    output: AgentReply | None
    messages: list[ModelMessage]


class ChatFailed(Exception):
    def __init__(self, error: Exception, messages: list[ModelMessage]):
        super().__init__(str(error))
        self.error, self.messages = error, messages


async def chat(message: str, deps: ShopDeps | None = None, history: list[ModelMessage] | None = None) -> ChatRun:
    """One shopper message in, one answer out. `history` = earlier messages (memory.py)."""
    deps = deps or ShopDeps()
    with capture_run_messages() as captured:
        try:
            result = await get_agent().run(with_page_note(message, deps), deps=deps,
                                           message_history=history or None, usage_limits=LIMITS)
        except AgentNotReady:
            raise
        except Exception as e:  # usage limit, model error, content filter... keep the loop for the audit
            raise ChatFailed(e, list(captured)[len(history or []):]) from e
    return ChatRun(result.output, result.new_messages())
