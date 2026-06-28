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

# --- GPU budget: evict idle to fit; refuse what can't fit ------------------
rb = ModelRegistry("d", max_models=10, factory=factory, budget_gb=30)
rb._estimate_gb = lambda mid: {"big": 20.0, "big2": 20.0, "small": 5.0}.get(mid, 0.0)
rb.get("big")  # 20 <= 30
rb.get("small")  # 20+5 = 25 <= 30
assert set(rb.loaded()) == {"big", "small"}
rb.get("big2")  # 25+20 = 45 > 30 -> evict idle LRU (big) so small+big2 = 25 fits
assert "big" not in rb.loaded() and {"small", "big2"} <= set(rb.loaded())
print("budget evicts idle to fit: OK")

# a model bigger than the whole budget is refused (evicting can't help)
rb2 = ModelRegistry("d", factory=factory, budget_gb=10)
rb2._estimate_gb = lambda mid: 25.0 if mid == "huge" else 0.0
try:
    rb2.get("huge")
    raise AssertionError("oversize model should have been refused")
except RuntimeError as e:
    assert "exceeds" in str(e), e
print("budget refuses oversize model: OK")

# budget full AND the remaining model is busy -> refuse (503), don't pile on
rb3 = ModelRegistry("d", max_models=10, factory=factory, budget_gb=30)
rb3._estimate_gb = lambda mid: 20.0
rb3.get("a").stats["active"] = True
try:
    rb3.get("b")
    raise AssertionError("should refuse: budget full + busy")
except RuntimeError as e:
    assert "busy" in str(e), e
print("budget full + busy -> refuse: OK")

# --- unload frees an idle model; refuses an active one ---------------------
ru = ModelRegistry("d", factory=factory)
ea = ru.get("a")
ru.get("b")
assert ru.unload("a") is True and ea.closed is True and "a" not in ru.loaded()
assert ru.unload("zzz") is False  # not loaded
ru.get("c")
ru.peek("c").stats["active"] = True
assert ru.unload("c") is False and "c" in ru.loaded()  # busy -> refuse
print("unload frees idle, refuses active: OK")

# --- info() summarizes loaded models (id, active, default) -----------------
ri = ModelRegistry("a", factory=factory)
ri.get("a")
ri.get("b")
info = {d["id"]: d for d in ri.info()}
assert set(info) == {"a", "b"}
assert info["a"]["default"] is True and info["b"]["default"] is False
assert info["a"]["active"] is False
print("info() summary: OK")

print("all registry tests passed")
