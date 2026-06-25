"""/memory: the pluggable backend layer (MemoryBackend port), the Memory
aggregator (search / recall / status / search rendering), and the command's
on/off toggle + /rag alias routing. Pure sqlite FTS5 — no model or server.

Run:  uv run python tests/test_memory.py
"""

import pathlib
import queue
import sys
import tempfile
import time

sys.path.insert(0, ".")

from agent.adapters.retrieval.bm25 import Bm25Backend
from agent.adapters.tools.memory import Memory, _human_bytes
from agent.ports.memory import MemoryBackend
from agent.tui.commands import REGISTRY
from agent.tui.commands.memory import MemoryCommand, RagCommand


def _workspace() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "mod.py").write_text("def make_banana():\n    return 'banana split'\n")
    (root / "notes.md").write_text("# Notes\n\nThe quick brown fox jumps.\n")
    return root


# --- backend conformance + stats -------------------------------------------
root = _workspace()
b = Bm25Backend(root)
assert isinstance(b, MemoryBackend), "Bm25Backend must satisfy the MemoryBackend protocol"
b.refresh(root)
st = b.stats()
assert st["name"] == "bm25" and st["by_source"]["code"] == 1 and st["by_source"]["docs"] == 1
assert st["files"] == 2 and st["size_bytes"] > 0
hits = b.search("banana")
assert hits and hits[0]["path"] == "mod.py" and hits[0]["backend"] == "bm25"
print("Bm25Backend conformance + stats + search: OK")

assert _human_bytes(0) == "0 B" and _human_bytes(2048).endswith("KB")
print("_human_bytes: OK")


# --- Memory aggregator ------------------------------------------------------
m = Memory(root)
assert [bk.name for bk in m.backends] == ["bm25", "vector"]  # vector self-reports availability
out, err = m.recall("banana")
assert not err and "mod.py:1-3" in out and "banana" in out
assert m.recall("zzzznotfound")[0].startswith("no matches")
status = m.status_lines(recall_on=True)
assert status[0][0] == "memory  ·  recall ENABLED"
assert any("code" in t and "chunks" in t for t, _ in status)
assert m.status_lines(recall_on=False)[0][0].startswith("memory  ·  recall DISABLED")
sl = m.search_lines("banana")
assert "1 hit" in sl[0][0] and any("mod.py" in t for t, _ in sl)
assert "no hits" in m.search_lines("zzzznotfound")[0][0]
print("Memory recall / status_lines / search_lines: OK")


# --- command routing + /rag alias ------------------------------------------
mem = next(c for c in REGISTRY if c.name == "/memory")
rag = next(c for c in REGISTRY if c.name == "/rag")
assert isinstance(mem, MemoryCommand) and isinstance(rag, RagCommand)
assert mem.match("/memory search foo") == " search foo"
assert mem.match("/rag") is None  # /memory doesn't swallow /rag
assert rag.match("/rag on") == " on"  # alias is a prefix match too
assert mem.completions() == ["/memory", "/memory search", "/memory on", "/memory off"]
assert rag.completions() == ["/rag"]
# alias must dispatch ahead-of nothing else and AFTER /memory in the registry
names = [c.name for c in REGISTRY]
assert names.index("/memory") < names.index("/rag")
print("command routing + /rag alias + completions: OK")


# --- on/off toggles runner.rag (synchronous part) --------------------------
class FakeRunner:
    def __init__(self, root):
        self.rag = False
        self.memory = Memory(root)


class FakeApp:
    def __init__(self, root):
        self.runner = FakeRunner(root)
        self.writes: list[str] = []
        self.msg_q: queue.Queue = queue.Queue()

    def body_write(self, r):
        self.writes.append(str(r))

    def call_from_thread(self, fn, *a):  # run inline in tests
        fn(*a)


app = FakeApp(root)
mem.run(app, "on")
assert app.runner.rag is True
mem.run(app, "off")
assert app.runner.rag is False
rag.run(app, "on")  # alias toggles the same flag
assert app.runner.rag is True
time.sleep(0.2)  # let the off-thread status render land (best-effort)
assert any("recall" in w.lower() for w in app.writes)
print("/memory on/off (+ /rag alias) toggles runner.rag: OK")

print("all memory tests passed")
