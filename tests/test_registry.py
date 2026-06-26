"""ModelRegistry: load-on-demand, per-model caching + memos, and LRU eviction
(idle-first, never an actively-generating engine; load over cap if all busy).
Driven with a fake engine factory — no real model loads.

Run:  uv run python tests/test_registry.py
"""

import sys

sys.path.insert(0, ".")

from server.registry import ModelRegistry

_loads: list[str] = []


class FakeEngine:
    def __init__(self, mid: str):
        self.model_id = mid
        self.stats = {"active": False}
        self.closed = False

    def close(self):
        self.closed = True


def factory(mid: str) -> FakeEngine:
    _loads.append(mid)
    return FakeEngine(mid)


# --- load on demand + cache ------------------------------------------------
r = ModelRegistry("default", max_models=2, factory=factory)
a = r.get("a")
assert a.model_id == "a" and _loads == ["a"]
assert r.get("a") is a and _loads == ["a"], "same model must not reload"
print("load-on-demand + cache: OK")

# --- LRU eviction over the cap, with close() -------------------------------
r.get("b")
assert set(r.loaded()) == {"a", "b"}
r.get("c")  # over cap -> evict the LRU (a) and close it
assert set(r.loaded()) == {"b", "c"} and a.closed is True
print("LRU eviction + close (frees memory): OK")

# --- a recent touch protects a model from eviction -------------------------
r2 = ModelRegistry("d", max_models=2, factory=factory)
r2.get("a")
r2.get("b")
r2.get("a")  # touch a -> b becomes the LRU
r2.get("c")  # evicts b, keeps a
assert "a" in r2.loaded() and "b" not in r2.loaded()
print("LRU touch protects recently-used: OK")

# --- never evict an ACTIVE engine ------------------------------------------
r3 = ModelRegistry("d", max_models=2, factory=factory)
ga = r3.get("a")
r3.get("b")
ga.stats["active"] = True  # a is mid-generation (and the LRU)
r3.get("c")  # must evict idle b, NOT active a
assert "a" in r3.loaded() and "b" not in r3.loaded()
print("active engine is not evicted: OK")

# --- all loaded models busy -> load over the cap (don't kill a live stream) -
r4 = ModelRegistry("d", max_models=2, factory=factory)
r4.get("a").stats["active"] = True
r4.get("b").stats["active"] = True
r4.get("c")  # everything active -> exceed the cap rather than evict
assert set(r4.loaded()) == {"a", "b", "c"}
print("all-active -> load over cap (no kill): OK")

# --- per-model memos are isolated (never shared across models) -------------
r5 = ModelRegistry("d", factory=factory)
r5.memos("a")["k"] = 1
assert r5.memos("b") == {} and r5.memos("a") == {"k": 1}
r5.get("a")  # peek finds a model only once it's actually loaded
assert r5.peek("zzz") is None and r5.peek("a") is not None
print("per-model memos isolated + peek: OK")

print("all registry tests passed")
