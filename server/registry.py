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
    def __init__(self, default_model: str, max_models: int | None = None, factory=make_engine):
        self.default_model = default_model
        self._max = max_models or int(os.environ.get("KAS_MAX_MODELS", "2"))
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
                self._evict_to_make_room()
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

    def peek(self, model_id: str | None = None) -> EngineLike | None:
        """The engine for a model if already loaded (no load) — for stats/cancel."""
        with self._lock:
            return self._engines.get(model_id or self.default_model)

    def most_recent(self) -> EngineLike | None:
        with self._lock:
            return next(reversed(self._engines.values()), None) if self._engines else None

    # -- eviction -------------------------------------------------------------

    def _evict_to_make_room(self) -> None:
        victims: list[tuple[str, EngineLike]] = []
        with self._lock:
            while len(self._engines) >= self._max:
                vid = self._idle_lru_locked()
                if vid is None:  # every loaded model is busy — load over the cap
                    log.warning("model cap %d reached but all active; loading over cap", self._max)
                    break
                victims.append((vid, self._engines.pop(vid)))
                self._memos.pop(vid, None)
        for vid, eng in victims:  # close outside the lock (frees the GPU memory)
            try:
                getattr(eng, "close", lambda: None)()
            except Exception:
                log.info("close of evicted model %s failed", vid, exc_info=True)
            log.info("evicted model %s (LRU)", vid)

    def _idle_lru_locked(self) -> str | None:
        """Oldest model that isn't mid-generation, or None if all are busy."""
        for mid, eng in self._engines.items():  # OrderedDict: oldest first
            if not getattr(eng, "stats", {}).get("active"):
                return mid
        return None
