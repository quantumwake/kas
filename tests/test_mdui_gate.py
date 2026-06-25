"""Guards the MDUI gate: the markdown-UI rendering is OFF by default (so the
TUI stays on the known-good plain path), and each feature turns on independently
for isolating the rich-output regression. Drives TuiIO with a fake app — no
Textual runtime. No model/server.

Run:  uv run python tests/test_mdui_gate.py
"""

import sys

sys.path.insert(0, ".")

from rich.markdown import Markdown

from agent.tui.io import TuiIO


class FakeApp:
    def __init__(self, md: bool, rule: bool) -> None:
        self.calls: list[str] = []
        self._mdui_md = md
        self._mdui_rule = rule
        self._agent_header_pending = True
        self.tok_in = self.tok_out = 0

    def call_from_thread(self, fn, *a) -> None:
        fn(*a)

    def body_write(self, r) -> None:
        self.calls.append("md" if isinstance(r, Markdown) else "text")

    def turn_rule(self, label: str, color: str) -> None:
        self.calls.append("rule")


def drive(md: bool, rule: bool) -> list[str]:
    app = FakeApp(md, rule)
    io = TuiIO(app)
    io.stream_started()
    io.delta("text", "# hi\n**bold**\n")
    io.tool_call("bash", {"x": 1})
    io.stream_finished(None)
    return app.calls


# default (both gates off) = the known-good plain path: no Markdown, no rules
off = drive(False, False)
assert "md" not in off and "rule" not in off, off
print("default OFF: no markdown, no rules — known-good plain path")

# markdown gate only: answer rendered as Markdown, still no rules
md = drive(True, False)
assert "md" in md and "rule" not in md, md
print("MD gate: markdown on, rules off")

# rules gate only: turn separators, but no Markdown
rule = drive(False, True)
assert "rule" in rule and "md" not in rule, rule
print("RULES gate: rules on, markdown off")

print("all mdui-gate tests passed")
