"""Memory-store registry + install plans (OS / arch aware).

Names which recall backends exist (bm25, vector), whether each is INSTALLED on
this host, and the platform-correct way to install the optional ones — so
`/memory` can show real state and offer to install only what this OS/arch
supports. Same philosophy as the embedder/engine registries: the wrong runtime is
never offered. Which stores are ENABLED persists to ~/.kascode/memory.json.
"""

import importlib.util
import json
import platform
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CONFIG = Path.home() / ".kascode" / "memory.json"


def _have(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _vector_installed() -> bool:
    # the vector store needs sqlite-vec AND a real (non-floor) embedder
    if not _have("sqlite_vec"):
        return False
    from ..embeddings import has_real_embedder

    return has_real_embedder()


def _build_bm25(workdir):
    from .bm25 import Bm25Backend

    return Bm25Backend(workdir)


def _build_vector(workdir):
    from .vector import VectorBackend

    return VectorBackend(workdir)


@dataclass(frozen=True)
class StoreSpec:
    name: str
    label: str
    build: Callable  # (workdir) -> MemoryBackend
    supported: Callable[[], bool]  # does this OS/arch support it at all?
    installed: Callable[[], bool]  # are its packages present here?
    default_on: bool  # enabled by default (when installed)?


STORES: dict[str, StoreSpec] = {
    "bm25": StoreSpec(
        "bm25", "BM25 lexical (sqlite FTS5)", _build_bm25, lambda: True, lambda: True, True
    ),
    "vector": StoreSpec(
        "vector",
        "semantic vectors (sqlite-vec)",
        _build_vector,
        lambda: True,
        _vector_installed,
        True,
    ),
}


# A memory STORE's own packages (no embedder). The vector store needs an embedder
# too, but the embedder FORMAT is a separate, chip-dependent choice (below) — not
# a memory store. kg (later) goes here as well.
STORE_INSTALL: dict[str, list[str]] = {"vector": ["sqlite-vec"]}


@dataclass(frozen=True)
class InstallPlan:
    packages: list[str]
    supported: Callable[[], bool]
    note: str


# Embedder FORMATS = model loaders for a chip type, exactly like the inference
# engine backends (mlx for Apple/Metal, gguf for llama.cpp, model2vec static CPU).
# Picked per host; the default is the portable CPU one. These are NOT memory
# stores — they're how the vector store turns text into vectors.
DEFAULT_EMBEDDER = "model2vec"
EMBEDDER_INSTALL: dict[str, InstallPlan] = {
    "model2vec": InstallPlan(["model2vec"], lambda: True, "portable CPU static embeddings"),
    "mlx": InstallPlan(["mlx-embeddings"], _is_apple_silicon, "Apple Silicon GPU (Metal)"),
    "gguf": InstallPlan(["llama-cpp-python"], lambda: True, "cross-platform GGUF (llama.cpp)"),
}


def _load_enabled() -> set[str] | None:
    try:
        return set(json.loads(CONFIG.read_text()).get("enabled", []))
    except (OSError, json.JSONDecodeError):
        return None


def enabled_stores() -> set[str]:
    """Persisted enabled set, or the default_on stores if nothing's saved yet."""
    saved = _load_enabled()
    return saved if saved is not None else {n for n, s in STORES.items() if s.default_on}


def set_enabled(name: str, on: bool) -> set[str]:
    en = enabled_stores()
    en.add(name) if on else en.discard(name)
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({"enabled": sorted(en)}))
    except OSError:
        pass
    return en


def install_command(store: str, embedder: str | None = None) -> tuple[list[str] | None, str]:
    """Build the platform-correct install argv for a memory STORE plus (for the
    vector store) its EMBEDDER format. Returns (argv, "") on success, or
    (None, reason) if the store/embedder is unknown or unsupported on this host.

    The embedder format defaults to model2vec (portable CPU); mlx/gguf are the
    chip-native alternatives, gated by platform. Prefers `uv pip`, else pip."""
    if store not in STORE_INSTALL:
        return None, f"unknown store {store!r} (installable: {', '.join(STORE_INSTALL)})"
    packages = list(STORE_INSTALL[store])
    if store == "vector":  # the vector store needs an embedder
        fmt = embedder or DEFAULT_EMBEDDER
        plan = EMBEDDER_INSTALL.get(fmt)
        if plan is None:
            return None, f"unknown embedder format {fmt!r} (have: {', '.join(EMBEDDER_INSTALL)})"
        if not plan.supported():
            return None, f"embedder {fmt!r} isn't supported on this OS/arch"
        packages += plan.packages
    if shutil.which("uv"):
        return ["uv", "pip", "install", "--python", sys.executable, *packages], ""
    return [sys.executable, "-m", "pip", "install", *packages], ""
