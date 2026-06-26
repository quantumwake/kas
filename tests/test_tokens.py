"""Cumulative token counter: input / output / cached accumulate from usage (incl.
cache_read / cache_creation), the compact status-bar summary formats, and /status
prints the full breakdown.

Run:  uv run python tests/test_tokens.py
"""

import asyncio
import pathlib
import queue
import sys
import tempfile

sys.path.insert(0, ".")

import anthropic

from agent.tui import AgentApp
from agent.tui.commands.status import StatusCommand


class _Usage:
    def __init__(self, i, o, cr=0, cc=0):
        self.input_tokens = i
        self.output_tokens = o
        self.cache_read_input_tokens = cr
        self.cache_creation_input_tokens = cc


# --- /status breakdown via a fake app (no runtime needed) ------------------
class _Runner:
    yolo = False
    rag = False
    net = False


class _App:
    def __init__(self):
        self.model, self.workdir, self.turns = "m", "/w", 0
        self.runner = _Runner()
        self.tok_in, self.tok_out, self.tok_cache_read, self.tok_cache_create = 1200, 300, 8000, 500
        self.writes: list[str] = []
        self.msg_q: queue.Queue = queue.Queue()

    def body_write(self, r):
        self.writes.append(str(r))


app = _App()
StatusCommand().run(app, "")
blob = "\n".join(app.writes)
assert "tokens:" in blob and "1200 in" in blob and "300 out" in blob
assert "8000 cached (read)" in blob and "500 cached (write)" in blob and "1500 total" in blob
print("/status token breakdown: OK")


# --- accumulation through io.stream_finished (real app) --------------------
async def _t() -> None:
    app = AgentApp(
        client=anthropic.Anthropic(base_url="http://127.0.0.1:9", api_key="x", max_retries=0),
        model="m",
        base_url="http://127.0.0.1:9",
        workdir=pathlib.Path(tempfile.mkdtemp()),
        yolo=False,
    )
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.2)
        assert (app.tok_in, app.tok_out, app.tok_cache_read) == (0, 0, 0)
        for _ in range(2):
            app.io.stream_started()
            app.io.stream_finished(_Usage(1200, 300, cr=8000, cc=500))
        assert app.tok_in == 2400 and app.tok_out == 600
        assert app.tok_cache_read == 16000 and app.tok_cache_create == 1000
        summary = app._token_summary()
        assert "2.4k↑" in summary and "600↓" in summary and "16.0k⚡" in summary
        # no cache reported -> no ⚡ segment
        app.tok_cache_read = 0
        assert "⚡" not in app._token_summary()
        # the /stats panel line renders the full breakdown without error
        line = str(app._stats_line({}))
        assert "in 2.4k" in line and "out 600" in line and "total 3.0k" in line


asyncio.run(_t())
print("token accumulation (incl. cached) + status-bar summary + /stats: OK")
print("all token tests passed")
