"""Live integration test against a REAL running kas server (exercises the MLX
engine — the one module the CPU suite can't cover). It SKIPS cleanly when no
server is reachable, so it's safe in CI; locally (`make start` first, or any
server on KAS_BASE_URL) it runs real generation.

Asserts structural invariants only (not specific model text), so it's robust
across models: non-empty generation, positive token accounting, and that the
streamed deltas reconstruct the final message.

Run:  make test-gpu     (or)     uv run python tests/test_engine_live.py
"""

import os
import sys

import anthropic
import httpx

sys.path.insert(0, ".")

BASE = os.environ.get("KAS_BASE_URL", "http://127.0.0.1:8765")


def _server_model() -> str | None:
    try:
        return httpx.get(BASE + "/v1/models", timeout=3).json()["data"][0]["id"]
    except Exception:
        return None


model = _server_model()
if model is None:
    print(f"SKIP test_engine_live: no server reachable at {BASE} (start one with `make start`)")
else:
    client = anthropic.Anthropic(base_url=BASE, api_key="local", max_retries=0, timeout=180)

    # --- non-streaming generation ------------------------------------------
    resp = client.messages.create(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": "Reply with exactly the word: pong"}],
    )
    texts = [b.text for b in resp.content if b.type == "text"]
    assert texts and any(t.strip() for t in texts), resp.content
    assert resp.usage.input_tokens > 0 and resp.usage.output_tokens > 0, resp.usage
    assert resp.stop_reason in ("end_turn", "max_tokens", "stop_sequence", "tool_use")
    print(f"live non-streaming: OK ({resp.usage.input_tokens}->{resp.usage.output_tokens} tok)")

    # --- streaming: deltas must reconstruct the final message --------------
    with client.messages.stream(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": "List three colors, one per line."}],
    ) as stream:
        deltas = list(stream.text_stream)
        final = stream.get_final_message()
    final_text = "".join(b.text for b in final.content if b.type == "text")
    assert "".join(deltas) == final_text, ("".join(deltas), final_text)
    assert final.stop_reason in ("end_turn", "max_tokens", "stop_sequence")
    print(f"live streaming: OK ({len(deltas)} deltas, {len(final_text)} chars)")

    # --- tool tokenization + parse path (lenient: the model may or may not
    #     choose to call, but the round-trip must succeed and stay structured) -
    tools = [
        {
            "name": "get_time",
            "description": "Return the current time. Call this to answer time questions.",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        }
    ]
    resp = client.messages.create(
        model=model,
        max_tokens=64,
        tools=tools,
        messages=[{"role": "user", "content": "What time is it? Use the get_time tool."}],
    )
    kinds = [b.type for b in resp.content]
    assert resp.usage.input_tokens > 0
    assert all(k in ("text", "thinking", "tool_use") for k in kinds), kinds
    if "tool_use" in kinds:
        tool = next(b for b in resp.content if b.type == "tool_use")
        assert tool.name == "get_time", tool.name
    print(f"live tool path: OK (blocks={kinds}, stop={resp.stop_reason})")

    print("all engine-live tests passed")
