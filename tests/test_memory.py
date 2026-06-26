"""/memory: pluggable backend layer (MemoryBackend port), the Memory aggregator
(recall / status / search), the store manager (enable/disable persistence,
platform-aware install plans), and command routing.

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
    enabled_stores,
    install_command,
    set_enabled,
)
from agent.adapters.tools.memory import Memory, _human_bytes
from agent.ports.memory import MemoryBackend
from agent.tui.commands import REGISTRY
from agent.tui.commands.memory import MemoryCommand


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


# --- reindex (incremental + full rebuild) and clear ------------------------
inc = m.reindex_lines(full=False)
assert "reindex (incremental)" in inc[0][0]
assert any("bm25:" in t and "0 file" in t for t, _ in inc), "already indexed -> 0 on rescan"
full = m.reindex_lines(full=True)
assert "full rebuild" in full[0][0]
assert any("bm25: 2 file" in t for t, _ in full), "wipe + rebuild re-indexes both files"
# clear drops the index db; a later search transparently rebuilds it
cl = m.clear_lines()
assert any("bm25: index dropped" in t for t, _ in cl)
assert not m._instance("bm25").db_path.exists(), "clear removed the index db file"
assert m.search("banana"), "search transparently rebuilds after a clear"
print("reindex (incremental + full) + clear: OK")


# --- status: recall state + per-store platform/install/enabled state -------
status = m.status_lines(recall_on=True)
text = "\n".join(t for t, _ in status)
assert status[0][0] == "memory  ·  recall ENABLED"
assert "● bm25" in text and any("code" in t and "chunks" in t for t, _ in status)
assert "⤓ vector — available, not installed" in text  # offers the install
assert "/memory install vector" in text
# the embedder is a chip-dependent SUB-choice of the vector store, not its own store
assert "embedder format (chip-dependent)" in text
assert m.status_lines(recall_on=False)[0][0].startswith("memory  ·  recall DISABLED")
print("status shows stores + install offer + embedder sub-choice: OK")


# --- store manager: enable/disable persists; installs are store + embedder fmt
assert enabled_stores() == {"bm25", "vector"}  # defaults (default_on)
set_enabled("vector", False)
assert "vector" not in enabled_stores()
assert stores.CONFIG.exists(), "enabled-set persisted to disk"
set_enabled("vector", True)
assert "vector" in enabled_stores()

# install_command(store, embedder): the default embedder is model2vec; mlx/gguf
# are embedder FORMATS (chip-gated), NOT separate stores
cmd, err = install_command("vector")
assert err == "" and cmd[-2:] == ["sqlite-vec", "model2vec"], cmd
assert install_command("mlx")[0] is None  # 'mlx' is not a store
assert install_command("vector", "bogusfmt")[0] is None  # unknown embedder format
import platform as _plat

is_apple = _plat.system() == "Darwin" and _plat.machine() == "arm64"
assert (install_command("vector", "mlx")[0] is not None) == is_apple, "mlx is Apple-gated"
assert install_command("vector", "gguf")[0] is not None  # cross-platform
print("store manager: enable/disable persistence + store+embedder install: OK")


# --- command routing (no /rag alias anymore) -------------------------------
mem = next(c for c in REGISTRY if c.name == "/memory")
assert isinstance(mem, MemoryCommand)
assert not any(c.name == "/rag" for c in REGISTRY), "/rag alias was removed"
assert mem.match("/memory enable vector") == " enable vector"
assert mem.completions()[0] == "/memory" and "/memory install" in mem.completions()
print("command routing + no /rag alias: OK")


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
mem.run(app, "on")  # back on for the rest of the checks
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
