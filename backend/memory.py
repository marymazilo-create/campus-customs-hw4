"""Campus Customs Shop: customer chat memory (MGT 409 HW 4, Problem 8).

Logged-in shoppers' chats are saved in the `chat_messages` table and reloaded when they
come back. The agent reads the last HISTORY_TURNS exchanges (one shopper message + one
Will reply = one exchange). Guests aren't saved; their open chat window is sent along
with each message instead, so Will can follow the conversation until they close the tab.

chat_messages: id, user_id, role ("user" | "assistant"), content, products_json, created_at
  products_json: the product cards shown with that reply, as a JSON list (or NULL)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from models import GuestTurn, HistoryMessage

HISTORY_TURNS = 15  # the agent remembers the last 15 exchanges (30 messages)


def _product_ids(products_json: str | None) -> list[str]:
    """Product ids from a saved reply. Works for the seed rows (full product dicts) and ours (cards)."""
    if not products_json:
        return []
    try:
        data = json.loads(products_json)
    except ValueError:
        return []
    items = data.get("products", []) if isinstance(data, dict) else data
    return [p["product_id"] for p in items if isinstance(p, dict) and p.get("product_id")]


def load_rows(conn: sqlite3.Connection, user_id: int, turns: int = HISTORY_TURNS) -> list[sqlite3.Row]:
    """The user's most recent messages, oldest first."""
    rows = conn.execute(
        "SELECT id, role, content, products_json, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, turns * 2),
    ).fetchall()
    rows = list(reversed(rows))
    while rows and rows[0]["role"] != "user":  # start on a shopper message, not half an exchange
        rows.pop(0)
    return rows


def for_widget(rows: list[sqlite3.Row]) -> list[HistoryMessage]:
    """Saved messages in the shape the chat widget shows when it reloads."""
    return [
        HistoryMessage(
            role="user" if r["role"] == "user" else "assistant",
            text=r["content"],
            product_count=len(_product_ids(r["products_json"])),
            created_at=r["created_at"],
        )
        for r in rows
    ]


def _assistant_text(content: str, product_ids: list[str]) -> str:
    # Tell the agent which cards were on the page with that reply, so "the second one" still works.
    if product_ids:
        return f"{content}\n[Product cards shown on the page: {', '.join(product_ids)}]"
    return content


def to_model_messages(rows: list[sqlite3.Row]) -> list[ModelMessage]:
    """Saved rows -> PydanticAI message history (what the agent "remembers")."""
    history: list[ModelMessage] = []
    for r in rows:
        ts = _parse_time(r["created_at"])
        if r["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=r["content"], timestamp=ts)]))
        else:
            text = _assistant_text(r["content"], _product_ids(r["products_json"]))
            history.append(ModelResponse(parts=[TextPart(content=text)], timestamp=ts))
    return history


def guest_messages(turns: list[GuestTurn]) -> list[ModelMessage]:
    """A guest's open chat window -> message history (last HISTORY_TURNS exchanges only)."""
    turns = turns[-HISTORY_TURNS * 2:]
    while turns and turns[0].role != "user":
        turns = turns[1:]
    out: list[ModelMessage] = []
    for t in turns:
        if t.role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=t.text)]))
        else:
            out.append(ModelResponse(parts=[TextPart(content=_assistant_text(t.text, t.product_ids))]))
    return out


def save_exchange(conn: sqlite3.Connection, user_id: int, message: str, reply: str, cards: list[dict]) -> None:
    """Save one shopper message and Will's reply (with the cards he showed)."""
    products = json.dumps([{"product_id": c["product_id"], "name": c["name"], "price": c["price"]} for c in cards]) if cards else None
    conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, message))
    conn.execute(
        "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
        (user_id, reply, products),
    )
    conn.commit()


def _parse_time(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
