"""Model registry: multiple loaded engines, routed by model id.

Replaces the single global engine. Each model_id maps to its own EngineLike (own
worker + KV slots + continuation memos), so different agents can use different
models without the slow offload+reload swap — and they interleave on the GPU
instead of one fully blocking the other.

Engines load on demand and are evicted LRU when over the model cap (KAS_MAX_MODELS)
— idle ones first, never one that's actively generating; if every loaded model is
busy we load over the cap rather than kill a live stream. Thread-safe: FastAPI
runs handlers in a threadpool, so the heavy load happens OUTSIDE the lock behind a
load-once guard (concurrent requests for the same model wait for one loader).
"""

import logging
import os
import threading
from collections import OrderedDict

from .backends import make_engine
from .core.ports import EngineLike

log = logging.getLogger("kas.registry")


class ModelRegistry:
    def __init__(
        self,
        default_model: str,
        max_models: int | None = None,
        factory=make_engine,
        budget_gb: float | None = None,
    ):
        self.default_model = default_model
        self._max = max_models or int(os.environ.get("KAS_MAX_MODELS", "2"))
        # GPU memory budget (GB). 0 = count-cap only. Estimated from on-disk
        # weights so multiple big models can't co-reside past what the GPU holds
        # — the over-cap path was what let Qwen3.6-35B + gemma-31b + a VLM pile up
        # and trip the Metal command-buffer timeout.
        self._budget_gb = (
            budget_gb if budget_gb is not None else float(os.environ.get("KAS_GPU_BUDGET_GB", "0"))
        )
        self._factory = factory
        self._engines: OrderedDict[str, EngineLike] = OrderedDict()  # LRU: oldest first
        self._memos: dict[str, dict] = {}  # model_id -> {thread: continuation memo}
        self._loading: dict[str, threading.Event] = {}  # model_id -> load-in-progress
        self._lock = threading.Lock()

    # -- access ---------------------------------------------------------------

    def get(self, model_id: str | None = None) -> EngineLike:
        """Return the engine for `model_id`, loading it on demand. Blocks while a
        model loads; concurrent callers for the same model share one load."""
        model_id = model_id or self.default_model
        while True:
            with self._lock:
                eng = self._engines.get(model_id)
                if eng is not None:
                    self._engines.move_to_end(model_id)  # LRU touch
                    return eng
                ev = self._loading.get(model_id)
                loader = ev is None
                if loader:
                    ev = self._loading[model_id] = threading.Event()
            if not loader:
                ev.wait()  # someone else is loading this model — wait, then re-check
                continue
            try:
                self._evict_to_make_room(model_id)
                engine = self._factory(model_id)  # heavy: loads weights (outside lock)
            except BaseException:
                with self._lock:
                    self._loading.pop(model_id, None)
                ev.set()
                raise
            with self._lock:
                self._engines[model_id] = engine
                self._memos.setdefault(model_id, {})
                self._loading.pop(model_id, None)
            ev.set()
            log.info("loaded model %s (%d/%d slots)", model_id, len(self._engines), self._max)
            return engine

    def memos(self, model_id: str | None = None) -> dict:
        """Per-model continuation memos (model-specific — never shared across models)."""
        with self._lock:
            return self._memos.setdefault(model_id or self.default_model, {})

    def loaded(self) -> list[str]:
        with self._lock:
            return list(self._engines)

    def info(self) -> list[dict]:
        """Per-loaded-model summary for visibility (id, active, GPU GB, default)."""
        with self._lock:
            engines = list(self._engines.items())
            default = self.default_model
        out = []
        for mid, eng in engines:  # system_stats() called outside the lock
            s = getattr(eng, "stats", {}) or {}
            sysstats = getattr(eng, "system_stats", lambda: {})() or {}
            out.append(
                {
                    "id": mid,
                    "active": bool(s.get("active")),
                    "gpu_active_gb": sysstats.get("gpu_active_gb"),
                    "est_gb": round(self._estimate_gb(mid), 1) or None,
                    "context_length": getattr(eng, "context_length", None),
                    "dialect": getattr(getattr(eng, "dialect", None), "name", None),
                    "default": mid == default,
                }
            )
        return out

    def unload(self, model_id: str) -> bool:
        """Offload one model and free its GPU memory. Refuses a model that's
        actively generating (would break the live stream). True if it unloaded."""
        with self._lock:
            eng = self._engines.get(model_id)
            if eng is None:
                return False
            if getattr(eng, "stats", {}).get("active"):
                return False  # busy — don't yank it
            self._engines.pop(model_id, None)
            self._memos.pop(model_id, None)
        try:
            getattr(eng, "close", lambda: None)()
        except Exception:
            log.info("close on unload of %s failed", model_id, exc_info=True)
        log.info("unloaded model %s", model_id)
        return True

    def peek(self, model_id: str | None = None) -> EngineLike | None:
        """The engine for a model if already loaded (no load) — for stats/cancel."""
        with self._lock:
            return self._engines.get(model_id or self.default_model)

    def most_recent(self) -> EngineLike | None:
        with self._lock:
            return next(reversed(self._engines.values()), None) if self._engines else None

    # -- eviction -------------------------------------------------------------

    def _estimate_gb(self, model_id: str) -> float:
        """Rough GPU footprint of a model from its on-disk weights (safetensors
        size ~= resident size for these quants). 0.0 if not found — which makes
        the budget a no-op for that model rather than a hard error."""
        import glob
        import pathlib

        hub = pathlib.Path.home() / ".cache" / "huggingface" / "hub"
        d = hub / ("models--" + model_id.replace("/", "--"))
        snaps = sorted(glob.glob(str(d / "snapshots" / "*")))
        if not snaps:
            return 0.0
        p = pathlib.Path(snaps[-1])
        return sum(f.stat().st_size for f in p.glob("*.safetensors")) / 1e9

    def _evict_to_make_room(self, incoming: str) -> None:
        """Plan evictions to satisfy BOTH the count cap and the GPU budget, then
        commit. Raises RuntimeError (-> 503) if `incoming` can't fit even after
        evicting every idle model — instead of piling on and tripping the GPU."""
        inc_gb = self._estimate_gb(incoming) if self._budget_gb else 0.0
        if self._budget_gb and inc_gb > self._budget_gb:
            raise RuntimeError(
                f"model {incoming} (~{inc_gb:.0f}GB) exceeds "
                f"KAS_GPU_BUDGET_GB={self._budget_gb:.0f}GB"
            )
        victims: list[tuple[str, EngineLike]] = []
        with self._lock:
            idle = [m for m, e in self._engines.items() if not _active(e)]  # LRU order
            evicted: set[str] = set()

            def resident_after() -> float:
                return sum(self._estimate_gb(m) for m in self._engines if m not in evicted)

            for m in idle:
                over_count = (len(self._engines) - len(evicted)) >= self._max
                over_budget = bool(self._budget_gb) and resident_after() + inc_gb > self._budget_gb
                if not over_count and not over_budget:
                    break
                evicted.add(m)
            # still over budget after evicting all idle -> the rest are busy: refuse.
            if self._budget_gb and resident_after() + inc_gb > self._budget_gb:
                raise RuntimeError(
                    f"GPU budget {self._budget_gb:.0f}GB full and the remaining models "
                    f"are busy; cannot load {incoming} (~{inc_gb:.0f}GB) right now"
                )
            if (len(self._engines) - len(evicted)) >= self._max:
                log.warning("model cap %d reached but all active; loading over cap", self._max)
            for m in evicted:
                victims.append((m, self._engines.pop(m)))
                self._memos.pop(m, None)
        for vid, eng in victims:  # close outside the lock (frees the GPU memory)
            try:
                getattr(eng, "close", lambda: None)()
            except Exception:
                log.info("close of evicted model %s failed", vid, exc_info=True)
            log.info("evicted model %s (LRU)", vid)

    def _idle_lru_locked(self) -> str | None:
        """Oldest model that isn't mid-generation, or None if all are busy."""
        for mid, eng in self._engines.items():  # OrderedDict: oldest first
            if not _active(eng):
                return mid
        return None


def _active(eng: EngineLike) -> bool:
    return bool(getattr(eng, "stats", {}).get("active"))
