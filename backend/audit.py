"""Campus Customs Shop: append-only audit trail of the agent loop (MGT 409 HW 4, Problem 12).

Every chat message adds entries to output/audit_trail.json. The file is one JSON array that
only ever grows: new entries are written over the closing "]" and the "]" is put back, so
nothing already in the file is rewritten or wiped between runs or server restarts.

Each entry has:
  time         UTC timestamp
  run_id       ties together the entries for one shopper message
  event        run_start | model_step | tool_call | guardrail | run_end
  tool         tool name (tool_call), or the guardrail's name
  args         short arguments (tool_call) or what triggered a guardrail
  result       short result
  stop_reason  why that step or run stopped ("tool_call", "stop", "final_answer",
               "usage_limit", "blocked_by_filter", "rate_limited", "error", ...)

Privacy: no emails, names, passwords or tokens. Shoppers appear as "user 3" or "guest",
messages are run through the sensitive-info mask first, and every text is cut short.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent  # hw4/
AUDIT_PATH = ROOT / "output" / "audit_trail.json"
SHORT = 200  # every args/result text is cut to this many characters
_lock = threading.Lock()


def new_run_id() -> str:
    return uuid.uuid4().hex[:10]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def short(value: Any, limit: int = SHORT) -> str:
    """A compact one-line text version of anything, cut to `limit` characters."""
    if value is None:
        return ""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, list) and value and hasattr(value[0], "model_dump"):
        value = [v.model_dump() for v in value]
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append(entries: list[dict]) -> None:
    """Add entries to the end of the JSON array without rewriting what's already there."""
    if not entries:
        return
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = ",\n".join(json.dumps(e, ensure_ascii=False) for e in entries)
    with _lock:
        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            AUDIT_PATH.write_text("[\n" + body + "\n]\n", encoding="utf-8")
            return
        with open(AUDIT_PATH, "r+b") as f:
            f.seek(0, 2)
            pos = f.tell()
            # walk back past whitespace to the closing bracket
            while pos > 0:
                pos -= 1
                f.seek(pos)
                ch = f.read(1)
                if ch not in b" \n\r\t":
                    break
            if ch != b"]":  # not our format: start a fresh array next to it rather than damage it
                raise ValueError(f"{AUDIT_PATH} doesn't end with ']'; not appending")
            f.seek(pos)
            f.write(("" if _array_is_empty(f, pos) else ",\n").encode() + body.encode("utf-8") + b"\n]\n")
            f.truncate()


def _array_is_empty(f, close_pos: int) -> bool:
    f.seek(0)
    head = f.read(close_pos).strip()
    return head in (b"[", b"")


def entry(run_id: str, event: str, *, tool: str = "", args: Any = None, result: Any = None,
          stop_reason: str = "", time: str | None = None, **extra: Any) -> dict:
    e = {"time": time or now(), "run_id": run_id, "event": event, "tool": tool,
         "args": short(args), "result": short(result), "stop_reason": stop_reason}
    e.update({k: v for k, v in extra.items() if v is not None})
    return e


def from_messages(run_id: str, messages: list) -> list[dict]:
    """Turn one agent run's new messages into model_step and tool_call entries."""
    from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

    calls: dict[str, ToolCallPart] = {}
    out: list[dict] = []
    for m in messages:
        if isinstance(m, ModelResponse):
            tool_calls = [p for p in m.parts if isinstance(p, ToolCallPart)]
            for p in tool_calls:
                calls[p.tool_call_id] = p
            out.append(entry(
                run_id, "model_step",
                tool=", ".join(p.tool_name for p in tool_calls),
                args="asked for " + ", ".join(p.tool_name for p in tool_calls) if tool_calls else "answered",
                result=f"tokens in {m.usage.input_tokens}, out {m.usage.output_tokens}" if m.usage else "",
                stop_reason=str(m.finish_reason or ("tool_call" if tool_calls else "stop")),
                time=m.timestamp.isoformat(timespec="milliseconds") if m.timestamp else None,
            ))
        elif isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart):
                    call = calls.get(p.tool_call_id)
                    out.append(entry(
                        run_id, "tool_call", tool=p.tool_name,
                        args=call.args if call else "", result=p.content, stop_reason="returned",
                        time=p.timestamp.isoformat(timespec="milliseconds") if p.timestamp else None,
                    ))
                elif isinstance(p, RetryPromptPart) and p.tool_name:
                    call = calls.get(p.tool_call_id)
                    out.append(entry(
                        run_id, "tool_call", tool=p.tool_name,
                        args=call.args if call else "", result=p.content, stop_reason="retry",
                    ))
    return out
