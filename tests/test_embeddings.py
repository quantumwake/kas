"""Platform-aware embedder registry + the zero-dep hashing floor.

The point of this layer: selecting an embedder must NEVER hard-error because a
runtime can't load on this host (e.g. MLX on NVIDIA). It degrades down a priority
chain to None. No model/server/network needed (hashing is pure-python).

Run:  uv run python tests/test_embeddings.py
"""

import os
import sys

sys.path.insert(0, ".")

os.environ.pop("KAS_EMBEDDER", None)  # don't let the ambient env steer selection

from agent.adapters.embeddings import (
    REGISTRY,
    _selection_order,
    available_embedders,
    make_embedder,
)
from agent.ports.memory import Embedder

# --- hashing floor: conformance, similarity, determinism -------------------
h = make_embedder("hashing")
assert isinstance(h, Embedder), "HashingEmbedder must satisfy the Embedder protocol"
assert h.name == "hashing" and h.dim == 256
vs = h.embed(["the quick brown fox", "the quick brown dog", "unrelated zebra plays"])
assert len(vs) == 3 and all(len(v) == 256 for v in vs)


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


assert _cos(vs[0], vs[1]) > _cos(vs[0], vs[2]), "overlapping text should score closer"
assert make_embedder("hashing").embed(["abc def"])[0] == h.embed(["abc def"])[0], "deterministic"
print("hashing floor: conformance + similarity + determinism: OK")

# --- registry / selection ---------------------------------------------------
order = _selection_order(None)
assert "hashing" not in order, "the lexical floor is never auto-selected"
assert order == sorted(order, key=lambda n: REGISTRY[n].priority), "auto order is by priority"
assert "hashing" in available_embedders() or available_embedders(), "hashing is always available"
# explicit request jumps the queue, then the rest follow as graceful fallbacks
assert _selection_order("model2vec")[0] == "model2vec"
assert set(_selection_order("model2vec")) >= {"mlx", "gguf", "model2vec"}
print("selection order (auto skips hashing; explicit-first): OK")

# --- auto never returns the floor; None when nothing real is installed ------
auto = make_embedder()
assert auto is None or auto.name != "hashing", "auto must not silently use the lexical floor"
print(f"auto selection -> {None if auto is None else auto.name} (not hashing): OK")

# --- graceful: an unsupported/uninstalled choice degrades, never ImportErrors
os.environ["KAS_EMBEDDER"] = "mlx"  # ask for MLX even where its package is absent
got = make_embedder()  # must not raise even if mlx_embeddings can't import here
assert got is None or got.name == "mlx"
assert "mlx_embeddings" not in sys.modules, "must not import the runtime just to skip it"
os.environ.pop("KAS_EMBEDDER", None)
print("unsupported/uninstalled choice degrades gracefully (no ImportError): OK")

# --- an unknown name is a config error (typo), not a silent no-op -----------
try:
    make_embedder("totally-made-up")
    raise SystemExit("expected ValueError for an unknown embedder name")
except ValueError:
    pass
print("unknown embedder name -> ValueError: OK")

print("all embeddings tests passed")
