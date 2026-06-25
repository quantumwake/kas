"""sqlite-vec vector backend: KNN recall over embedded chunks, incremental
reindex, geometry-change rebuild, and RRF fusion with BM25 in the aggregator.

Uses the zero-dep HashingEmbedder (no model/network) so it's deterministic. When
sqlite-vec isn't installed it just prints "skipped" and returns (no SystemExit, so
the pytest characterization runner stays green). Run it with the extension (and
model2vec so the store registry counts vector as installed — the actual embedder
stays the deterministic hashing floor via KAS_EMBEDDER):

    uv run --with sqlite-vec --with model2vec python tests/test_vector.py
"""

import importlib.util
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, ".")

os.environ["KAS_EMBEDDER"] = "hashing"  # deterministic, offline; for the Memory path

import agent.adapters.retrieval.stores as stores

stores.CONFIG = pathlib.Path(tempfile.mkdtemp()) / "memory.json"  # isolate from $HOME

# These imports are safe without sqlite-vec (the extension is imported lazily,
# only inside VectorBackend methods once it's known to be available).
from agent.adapters.embeddings.hashing import HashingEmbedder
from agent.adapters.retrieval.vector import VectorBackend
from agent.adapters.tools.memory import Memory
from agent.ports.memory import MemoryBackend


def _workspace() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp())
    (root / "auth.py").write_text(
        "def login(user, password):\n    # verify credentials against the store\n"
        "    return check_password(user, password)\n"
    )
    (root / "math_utils.py").write_text("def add(a, b):\n    return a + b\n")
    return root


def _main() -> None:
    root = _workspace()

    # --- backend conformance + availability --------------------------------
    vb = VectorBackend(root, embedder=HashingEmbedder())
    assert isinstance(vb, MemoryBackend), "VectorBackend must satisfy MemoryBackend"
    assert vb.available(), "sqlite-vec present + embedder injected -> available"
    print("VectorBackend conformance + availability: OK")

    # --- index + KNN search ------------------------------------------------
    assert vb.refresh(root) >= 2, "both files embedded"
    hits = vb.search("verify credentials login user password")
    assert hits, "vector search returns hits"
    assert hits[0]["path"] == "auth.py" and hits[0]["backend"] == "vector", hits[0]
    assert all("score" in h for h in hits)  # distance
    print("vector KNN search ranks the relevant chunk first: OK")

    # --- incremental: unchanged -> no re-embed -----------------------------
    assert vb.refresh(root) == 0, "hash-skip: nothing re-indexed"
    print("incremental reindex (hash-skip): OK")

    # --- stats -------------------------------------------------------------
    st = vb.stats()
    assert "hashing" in st["label"] and st["by_source"].get("code") and st["files"] == 2
    assert st["size_bytes"] > 0
    print("vector stats: OK")

    # --- geometry change (different dim) rebuilds the store ----------------
    vb2 = VectorBackend(root, embedder=HashingEmbedder(dim=64))  # same db, new dim
    assert vb2.stats()["files"] == 0, "dim change wiped the old vectors"
    assert vb2.refresh(root) >= 2 and vb2.search("add numbers")  # rebuilds + searches
    print("embedder geometry change rebuilds the vector store: OK")

    # --- RRF fusion in the aggregator (bm25 + vector) ----------------------
    m = Memory(_workspace())  # fresh workspace; Memory builds its own bm25 + vector
    assert [b.name for b in m.backends] == ["bm25", "vector"]
    fused = m.search("verify credentials login")
    assert fused, "fused search returns hits"
    union = {bk for h in fused for bk in h.get("backends", [])}
    assert "bm25" in union and "vector" in union, f"both backends should contribute: {union}"
    assert fused[0]["path"] == "auth.py", "the relevant file fuses to the top"
    print("RRF fusion across bm25 + vector: OK")

    print("all vector tests passed")


if importlib.util.find_spec("sqlite_vec") is None:
    print(
        "test_vector: skipped (sqlite-vec not installed — pip install sqlite-vec / extra [memory])"
    )
else:
    _main()
