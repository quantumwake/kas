"""/memory: pluggable backend layer (MemoryBackend port), the Memory aggregator
(recall / status / search), the store manager (enable/disable persistence,
platform-aware install plans), and command routing + the /rag alias.

Pure sqlite FTS5 — no model/server. The persisted enabled-set is redirected to a
temp file so it never reads or writes the real ~/.kascode/memory.json.

Run:  uv run python tests/test_memory.py
"""

import pathlib
import queue
import sys
import tempfile
import time

sys.path.insert(0, ".")

import agent.adapters.retrieval.stores as stores

stores.CONFIG = pathlib.Path(tempfile.mkdtemp()) / "memory.json"  # isolate from $HOME

from agent.adapters.retrieval.bm25 import Bm25Backend
from agent.adapters.retrieval.stores import (
    INSTALLS,
    enabled_stores,
    install_command,
    set_enabled,
)
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
hits = b.search("banana")
assert hits and hits[0]["path"] == "mod.py" and hits[0]["backend"] == "bm25"
assert _human_bytes(0) == "0 B" and _human_bytes(2048).endswith("KB")
print("Bm25Backend conformance + stats + search: OK")


# --- Memory aggregator (vector not installed here -> bm25 only) -------------
m = Memory(root)
assert [bk.name for bk in m.backends] == ["bm25"], "only installed+enabled stores are active"
out, err = m.recall("banana")
assert not err and "mod.py:1-3" in out and "banana" in out
assert m.recall("zzzznotfound")[0].startswith("no matches")
sl = m.search_lines("banana")
assert "1 hit" in sl[0][0] and any("mod.py" in t for t, _ in sl)
print("Memory recall / search (active backends only): OK")


# --- status: recall state + per-store platform/install/enabled state -------
status = m.status_lines(recall_on=True)
text = "\n".join(t for t, _ in status)
assert status[0][0] == "memory  ·  recall ENABLED"
assert "● bm25" in text and any("code" in t and "chunks" in t for t, _ in status)
assert "⤓ vector — available, not installed" in text  # offers the install
assert "/memory install vector" in text
assert "embedders:" in text  # platform-filtered embedder availability
assert m.status_lines(recall_on=False)[0][0].startswith("memory  ·  recall DISABLED")
print("status shows stores + install offer + embedders: OK")


# --- store manager: enable/disable persists; install plans are platform-gated
assert enabled_stores() == {"bm25", "vector"}  # defaults (default_on)
set_enabled("vector", False)
assert "vector" not in enabled_stores()
assert stores.CONFIG.exists(), "enabled-set persisted to disk"
set_enabled("vector", True)
assert "vector" in enabled_stores()

# install_command: known bundles resolve to a pip argv; mlx is Apple-gated
assert "vector" in INSTALLS and install_command("vector")[-2:] == ["sqlite-vec", "model2vec"][-2:]
assert install_command("nope") is None  # unknown bundle
import platform as _plat

is_apple = _plat.system() == "Darwin" and _plat.machine() == "arm64"
assert (install_command("mlx") is not None) == is_apple, "mlx install offered only on Apple Silicon"
assert install_command("gguf") is not None  # cross-platform
print("store manager: enable/disable persistence + platform-gated install: OK")


# --- command routing + /rag alias ------------------------------------------
mem = next(c for c in REGISTRY if c.name == "/memory")
rag = next(c for c in REGISTRY if c.name == "/rag")
assert isinstance(mem, MemoryCommand) and isinstance(rag, RagCommand)
assert mem.match("/memory enable vector") == " enable vector"
assert mem.match("/rag") is None and rag.match("/rag on") == " on"
assert mem.completions()[0] == "/memory" and "/memory install" in mem.completions()
assert rag.completions() == ["/rag"]
assert [c.name for c in REGISTRY].index("/memory") < [c.name for c in REGISTRY].index("/rag")
print("command routing + /rag alias + completions: OK")


# --- /memory on/off + enable/disable through the command -------------------
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

    def call_from_thread(self, fn, *a):
        fn(*a)


app = FakeApp(root)
mem.run(app, "on")
assert app.runner.rag is True
mem.run(app, "off")
assert app.runner.rag is False
rag.run(app, "on")  # alias toggles the same flag
assert app.runner.rag is True
mem.run(app, "disable vector")
assert "vector" not in enabled_stores()
mem.run(app, "enable vector")
assert "vector" in enabled_stores()
mem.run(app, "enable bogusstore")
assert any("unknown store" in w for w in app.writes)
time.sleep(0.2)  # let off-thread status render land (best-effort)
print("/memory on/off + enable/disable + bad-store guard: OK")

print("all memory tests passed")
