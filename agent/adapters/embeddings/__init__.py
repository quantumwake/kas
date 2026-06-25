"""Embedder registry + selector (OS / arch / GPU aware) — the same shape as
server/backends, for the same reason: a runtime only exists on some platforms, so
each embedder declares whether the host SUPPORTS it and whether its package is
INSTALLED, both checked BEFORE the heavy import. `import mlx_embeddings` is never
attempted on an NVIDIA/Linux box.

Difference from the inference backends: embeddings are OPTIONAL. The vector memory
backend is a bonus on top of BM25 + KG, so selection FALLS BACK down a priority
chain and ultimately returns None (vector recall simply stays off) instead of
raising. Nothing errors because MLX can't load on the wrong chip — it's skipped.

Selection: explicit `name=` / KAS_EMBEDDER  >  best supported+installed by
priority. An unknown name is a config error (ValueError); a name that's just
unsupported/uninstalled here degrades to the next candidate. The zero-dependency
`hashing` embedder is never auto-selected (it's lexical, low quality) — it exists
as an explicit, fully-offline floor for testing or air-gapped use.
"""

import importlib.util
import os
import platform
from collections.abc import Callable
from dataclasses import dataclass

from ...ports.memory import Embedder

EmbedderFactory = Callable[[], Embedder]


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _has(module: str) -> Callable[[], bool]:
    # importable check WITHOUT importing — find_spec doesn't run the module, so a
    # platform-incompatible package is detected, not triggered.
    return lambda: importlib.util.find_spec(module) is not None


def _load_mlx() -> EmbedderFactory:
    from .mlx import MlxEmbedder

    return MlxEmbedder


def _load_gguf() -> EmbedderFactory:
    from .gguf import GgufEmbedder

    return GgufEmbedder


def _load_model2vec() -> EmbedderFactory:
    from .model2vec import Model2VecEmbedder

    return Model2VecEmbedder


def _load_hashing() -> EmbedderFactory:
    from .hashing import HashingEmbedder

    return HashingEmbedder


@dataclass(frozen=True)
class EmbedderSpec:
    load: Callable[[], EmbedderFactory]  # lazy: returns the constructor
    supported: Callable[[], bool]  # does this OS/arch support the runtime?
    installed: Callable[[], bool]  # is the package importable here?
    requires: str  # human note for /memory when unavailable
    priority: int  # lower = preferred in auto-selection
    auto: bool = True  # eligible for automatic selection?


# Add an embedder by dropping a module here + one registry line. Order by
# priority: native GPU runtimes first, portable CPU ones next, the floor last.
REGISTRY: dict[str, EmbedderSpec] = {
    "mlx": EmbedderSpec(
        load=_load_mlx,
        supported=_is_apple_silicon,
        installed=_has("mlx_embeddings"),
        requires="macOS on Apple Silicon + mlx-embeddings",
        priority=10,
    ),
    "gguf": EmbedderSpec(
        load=_load_gguf,
        supported=lambda: True,
        installed=_has("llama_cpp"),
        requires="llama-cpp-python (any OS) + a GGUF embedding model",
        priority=20,
    ),
    "model2vec": EmbedderSpec(
        load=_load_model2vec,
        supported=lambda: True,
        installed=_has("model2vec"),
        requires="model2vec (any OS, CPU, static embeddings)",
        priority=30,
    ),
    "hashing": EmbedderSpec(
        load=_load_hashing,
        supported=lambda: True,
        installed=lambda: True,  # pure-python, always available
        requires="(built in)",
        priority=90,
        auto=False,  # explicit-only: lexical, low quality
    ),
}


def available_embedders() -> list[str]:
    """Embedders that could run here right now (supported + installed)."""
    return [n for n, s in REGISTRY.items() if s.supported() and s.installed()]


def _selection_order(name: str | None) -> list[str]:
    auto = sorted(
        (n for n, s in REGISTRY.items() if s.auto),
        key=lambda n: REGISTRY[n].priority,
    )
    if not name:
        return auto
    if name not in REGISTRY:
        raise ValueError(
            f"unknown embedder {name!r} (have: {', '.join(sorted(REGISTRY))}). "
            "Set KAS_EMBEDDER to one of those."
        )
    # honour the request first, then degrade gracefully through the rest
    return [name, *(n for n in auto if n != name)]


def make_embedder(name: str | None = None) -> Embedder | None:
    """Return a ready Embedder, or None if nothing usable is installed here.

    Never raises for platform reasons — an unsupported/uninstalled choice is
    skipped, not fatal. The only error is an unknown name (a config typo)."""
    chosen = name or os.environ.get("KAS_EMBEDDER")
    for n in _selection_order(chosen):
        spec = REGISTRY[n]
        if spec.supported() and spec.installed():
            try:
                return spec.load()()  # lazy import + construct (may need a model)
            except Exception:
                continue  # model missing / load failed -> try the next candidate
    return None
