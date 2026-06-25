"""/spec wizard: the seed prompt and the command wiring (push the selection
modal, and on a chosen kind queue a SPEC-MODE turn). Driven with a fake app —
no Textual runtime. No model/server.

Run:  uv run python tests/test_spec.py
"""

import queue
import sys

sys.path.insert(0, ".")

from agent.core.spec import PROJECT_KINDS, spec_seed
from agent.tui.commands.spec import SpecCommand
from agent.tui.widgets import SpecWizard

# --- spec_seed -------------------------------------------------------------
seed = spec_seed("web app")
assert "SPEC MODE" in seed
assert "web app" in seed
assert "SPEC.md" in seed and "Checklist" in seed  # it instructs the spec doc
assert spec_seed("").endswith("other. Let's spec it out.")  # empty -> 'other'
assert "game" in PROJECT_KINDS and "other" in PROJECT_KINDS
print("spec_seed: OK")


# --- SpecCommand wiring ----------------------------------------------------
class FakeApp:
    def __init__(self, busy=False) -> None:
        self.busy = busy
        self.msg_q: queue.Queue = queue.Queue()
        self.writes: list[str] = []
        self.pushed = None  # (screen, callback)

    def body_write(self, r) -> None:
        self.writes.append(str(r))

    def push_screen(self, screen, callback) -> None:
        self.pushed = (screen, callback)


spec = SpecCommand()

# idle: /spec pushes the SpecWizard modal with a callback
app = FakeApp()
spec.run(app, "")
assert app.pushed is not None, "spec did not push a screen"
screen, cb = app.pushed
assert isinstance(screen, SpecWizard)

# choosing a kind queues a SPEC-MODE seed turn
cb("backend service / API")
seed = app.msg_q.get_nowait()
assert "SPEC MODE" in seed and "backend service / API" in seed
print("/spec -> modal -> seed turn: OK")

# cancelling the modal queues nothing
app2 = FakeApp()
spec.run(app2, "")
app2.pushed[1](None)
assert app2.msg_q.empty()
print("/spec cancel: nothing queued")

# busy: /spec defers and pushes no modal
busy = FakeApp(busy=True)
spec.run(busy, "")
assert busy.pushed is None and any("wait until the agent is idle" in w for w in busy.writes)
print("/spec while busy: OK")

print("all spec tests passed")
