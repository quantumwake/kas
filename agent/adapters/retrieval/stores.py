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


@dataclass(frozen=True)
class InstallPlan:
    packages: list[str]
    supported: Callable[[], bool]
    note: str


# Installable bundles -> concrete pip packages, platform-gated. Each is
# SELF-SUFFICIENT (includes sqlite-vec) so any one gives a working vector store:
# `vector` is the portable CPU default; `mlx`/`gguf` swap in a GPU/native embedder.
INSTALLS: dict[str, InstallPlan] = {
    "vector": InstallPlan(
        ["sqlite-vec", "model2vec"], lambda: True, "sqlite-vec + model2vec (portable CPU embedder)"
    ),
    "mlx": InstallPlan(
        ["sqlite-vec", "mlx-embeddings"],
        _is_apple_silicon,
        "sqlite-vec + mlx-embeddings (Apple Silicon GPU embedder)",
    ),
    "gguf": InstallPlan(
        ["sqlite-vec", "llama-cpp-python"],
        lambda: True,
        "sqlite-vec + llama-cpp-python (cross-platform GGUF embedder)",
    ),
}

# Which install bundle provides each embedder (for the /memory status hints):
# model2vec ships in the `vector` bundle; mlx/gguf bundles are named for theirs.
EMBEDDER_BUNDLE = {"model2vec": "vector", "mlx": "mlx", "gguf": "gguf"}


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


def install_command(name: str) -> list[str] | None:
    """The platform-correct install argv for an install bundle, or None if the
    bundle is unknown or unsupported on this host. Prefers `uv pip` (the project's
    installer), falling back to the running interpreter's pip."""
    plan = INSTALLS.get(name)
    if plan is None or not plan.supported():
        return None
    if shutil.which("uv"):
        return ["uv", "pip", "install", "--python", sys.executable, *plan.packages]
    return [sys.executable, "-m", "pip", "install", *plan.packages]
