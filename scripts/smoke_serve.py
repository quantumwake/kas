"""Smoke-test a RUNNING kas server (KAS_BASE_URL) — green lights or red.

Checks the served model end to end over the real HTTP/SSE path:
  1. streaming text  — a plain prompt streams non-empty text
  2. tool calling     — a forced tool call parses into a tool_use (NOT leaked as
                        text, which is what a dialect/format mismatch looks like)

Exit 0 if all green, 1 otherwise — so it drops into CI / a make target.

  make smoke-serve                 # against http://127.0.0.1:8765
  KAS_BASE_URL=… make smoke-serve
"""

import json
import os
import sys

import httpx

BASE = os.environ.get("KAS_BASE_URL", "http://127.0.0.1:8765").rstrip("/")


def _events(payload: dict):
    """Yield parsed SSE data objects from POST /v1/messages."""
    with httpx.stream("POST", BASE + "/v1/messages", json=payload, timeout=180) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith("data: "):
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    pass


def check_streaming() -> tuple[bool, str]:
    text, stop = "", None
    for ev in _events(
        {
            "model": "x",
            "max_tokens": 40,
            "stream": True,
            "messages": [{"role": "user", "content": "Say hello in exactly three words."}],
        }
    ):
        if ev.get("type") == "content_block_delta" and ev["delta"].get("type") == "text_delta":
            text += ev["delta"]["text"]
        elif ev.get("type") == "message_delta":
            stop = ev["delta"].get("stop_reason")
    ok = bool(text.strip())
    return ok, f"text={text.strip()[:50]!r} stop={stop}"


def check_tool_calling() -> tuple[bool, str]:
    tools = [
        {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        }
    ]
    tool_uses, leaked = [], ""
    for ev in _events(
        {
            "model": "x",
            "max_tokens": 300,
            "stream": True,
            "tool_choice": {"type": "any"},
            "tools": tools,
            "messages": [{"role": "user", "content": "Weather in Paris? Use the get_weather tool."}],
        }
    ):
        t = ev.get("type")
        if t == "content_block_start" and ev["content_block"].get("type") == "tool_use":
            tool_uses.append(ev["content_block"]["name"])
        elif t == "content_block_delta" and ev["delta"].get("type") == "text_delta":
            leaked += ev["delta"]["text"]
    ok = bool(tool_uses)
    detail = f"tool_uses={tool_uses}"
    if not ok and leaked.strip():
        detail += (
            f"  ⚠ LEAKED AS TEXT — the model's tool format isn't parsed by this "
            f"dialect: {leaked.strip()[:90]!r}"
        )
    return ok, detail


def main() -> int:
    try:
        info = httpx.get(BASE + "/v1/models", timeout=3).json()["data"][0]
    except Exception as exc:
        print(f"✗ no server at {BASE} — start one first: make start  ({exc})")
        return 1
    print(f"server: {info['id']}  ·  dialect: {info.get('dialect')}  ·  {BASE}\n")

    all_ok = True
    for name, fn in (("streaming text", check_streaming), ("tool calling", check_tool_calling)):
        try:
            ok, detail = fn()
        except Exception as exc:
            ok, detail = False, f"error: {type(exc).__name__}: {exc}"
        all_ok = all_ok and ok
        print(f"  {'✓' if ok else '✗'} {name:15s} {detail}")

    print("\n" + ("ALL GREEN ✓" if all_ok else "SOME CHECKS FAILED ✗"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
