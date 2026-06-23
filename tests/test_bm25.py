"""Characterization tests for the BM25 RagIndex: chunking, incremental
indexing (hash-skip), and ranked search over a tiny temp corpus. Pure sqlite
FTS5 — no model or server needed.

Run:  uv run python tests/test_bm25.py
"""

import pathlib
import sys
import tempfile

sys.path.insert(0, ".")

from agent.adapters.retrieval.bm25 import RagIndex, _chunk_code, _chunk_text, _match_query

# --- chunkers --------------------------------------------------------------
code = "def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n"
chunks = _chunk_code(code)
assert any("alpha" in body for _, _, body in chunks)
assert any("beta" in body for _, _, body in chunks)
assert _chunk_text("") == []  # empty -> no chunks
print("chunkers: OK")

# --- query normalization drops stopwords -----------------------------------
assert _match_query("") == ""  # nothing to match
assert "OR" in _match_query("how does the parser work")  # content words OR-joined
assert "how" not in _match_query("how does the parser work").split(" OR ")  # stopword dropped
print("match-query: OK")

# --- index + search over a temp workspace ----------------------------------
db = pathlib.Path(tempfile.mkdtemp()) / "rag.db"
idx = RagIndex(db)
root = pathlib.Path(tempfile.mkdtemp())
(root / "mod.py").write_text("def make_banana():\n    return 'banana split'\n")
(root / "notes.md").write_text("# Notes\n\nThe quick brown fox jumps high.\n")

assert idx.index_workspace(root) == 2  # both files indexed
assert idx.index_workspace(root) == 0  # unchanged -> hash-skip, nothing reindexed

hits = idx.search("banana")
assert hits and any("banana" in h["body"] for h in hits), hits
assert hits[0]["source"] == "code"
assert "mod.py" in hits[0]["path"]

docs = idx.search("brown fox")
assert docs and any("fox" in h["body"] for h in docs), docs
assert docs[0]["source"] == "docs"

assert idx.search("") == []  # empty query short-circuits
print("index/search: OK")

# --- incremental: a changed file is re-indexed -----------------------------
(root / "mod.py").write_text("def make_cherry():\n    return 'cherry pie'\n")
assert idx.index_workspace(root) == 1  # only the changed file
assert idx.search("cherry"), "new content should be searchable"
print("incremental reindex: OK")

print("all bm25 tests passed")
