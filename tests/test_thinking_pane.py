"""Unit tests for the TUI live thinking pane buffering (TuiIO._push_thinking /
_end_thinking): reasoning accumulates into the bounded pane, then collapses to a
one-line marker — and a second end is a no-op.

Run:  uv run python tests/test_thinking_pane.py
"""

import sys

sys.path.insert(0, ".")

from agent.tui.io import TuiIO


class _FakeApp:
    """Minimal stand-in: runs UI calls inline and records what the pane did."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._mdui_md = False  # plain mode (the path the pane lives on)

    def call_from_thread(self, fn, *a) -> None:
        fn(*a)

    def update_thinking(self, lines) -> None:
        self.calls.append(("update", list(lines)))

    def hide_thinking(self) -> None:
        self.calls.append(("hide",))

    def body_write(self, renderable) -> None:
        self.calls.append(("body", str(renderable)))


app = _FakeApp()
io = TuiIO(app)

# reasoning accumulates; the latest pane update carries the running lines
io._push_thinking("alpha\nbeta\n")
io._push_thinking("gamma")
updates = [c for c in app.calls if c[0] == "update"]
assert updates, app.calls
joined = "\n".join(updates[-1][1])
assert "alpha" in joined and "gamma" in joined, joined

# ending the reasoning leaves a collapsed marker in the transcript + hides the pane
io._end_thinking()
assert any(c[0] == "body" and "thought" in c[1] for c in app.calls), app.calls
assert app.calls[-1] == ("hide",), app.calls

# a second end is a no-op (pane already collapsed) — no duplicate marker/hide
n = len(app.calls)
io._end_thinking()
assert len(app.calls) == n, app.calls

print("thinking pane tests passed")
