"""Campus Customs Shop: safety checks the code enforces (MGT 409 HW 4, Problem 12).

The prompt asks Will to behave; these make sure of it, whatever the model does.

  mask_sensitive   card numbers, SSNs and typed passwords are masked BEFORE the message
                   reaches the model, the saved chat history or the audit trail
  check_prices     every $ amount in Will's reply must match a price that came from the
                   database this turn; anything else is removed and flagged
  check_discounts  replies that offer a promo code, coupon or "% off" are replaced
  RateLimiter      at most RATE_LIMIT messages per RATE_WINDOW seconds per shopper
"""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque

# ---------- 1. mask sensitive info ----------

CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
SSN = re.compile(r"(?<!\d)\d{3}[- ]\d{2}[- ]\d{4}(?!\d)")
PASSWORD = re.compile(r"(?i)\b(pass(?:word|code)|pwd|pin)\b(\s*(?:is|was|=|:)\s*)(\S+)")


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
        alt = not alt
    return total % 10 == 0


def mask_sensitive(text: str) -> tuple[str, list[str]]:
    """Return the text with sensitive info masked, and what kinds were found."""
    found: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            found.append("card number")
            return "[card number removed]"
        return m.group(0)

    text = CARD.sub(card, text)
    if SSN.search(text):
        found.append("SSN")
        text = SSN.sub("[SSN removed]", text)
    if PASSWORD.search(text):
        found.append("password")
        text = PASSWORD.sub(lambda m: f"{m.group(1)}{m.group(2)}[removed]", text)
    return text, found


SENSITIVE_NOTE = ("Heads up: please don't type card numbers, Social Security numbers or passwords in chat. "
                  "I removed it before anyone could see it. ")

# ---------- 2. price double-check ----------

DOLLARS = re.compile(r"\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def amounts_in(text: str) -> set[float]:
    return {round(float(m.group(1).replace(",", "")), 2) for m in DOLLARS.finditer(text)}


def check_prices(reply: str, allowed: set[float]) -> tuple[str, list[str]]:
    """Remove any sentence quoting a $ amount that isn't a real price from this turn."""
    bad = [m.group(1) for m in DOLLARS.finditer(reply) if round(float(m.group(1).replace(",", "")), 2) not in allowed]
    if not bad:
        return reply, []
    kept = [s for s in SENTENCE.split(reply)
            if not any(round(float(m.group(1).replace(",", "")), 2) not in allowed for m in DOLLARS.finditer(s))]
    cleaned = " ".join(kept).strip()
    note = "The cards on the page show the current prices."
    return (f"{cleaned} {note}".strip() if cleaned else note), bad

# ---------- 3. no discount codes ----------

DISCOUNT = re.compile(r"(?i)\b(promo|coupon|discount|voucher)\s*codes?\b|\b\d{1,2}\s?%\s*off\b|\bpercent off\b")
NO_DISCOUNT_REPLY = ("Can't do discounts or codes, cousin or not. The price on the card is the price. "
                     "Want help finding something in your budget instead?")


def check_discounts(reply: str) -> tuple[str, bool]:
    if DISCOUNT.search(reply):
        return NO_DISCOUNT_REPLY, True
    return reply, False

# ---------- 4. message rate limit ----------

RATE_LIMIT = 8     # messages
RATE_WINDOW = 60   # seconds
RATE_REPLY = "Whoa, slow down. My cousin says I can only handle so many questions a minute. Give it a few seconds and try again."


class RateLimiter:
    """At most `limit` messages per `window` seconds for each shopper (user id or browser address)."""

    def __init__(self, limit: int = RATE_LIMIT, window: float = RATE_WINDOW):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True
