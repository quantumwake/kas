"""Backend selection (server/backends): OS/arch-aware routing, exercised without
loading a real model. Verifies the registry, model-id+platform detection, and
the clear errors for an unknown or platform-unsupported backend (e.g. MLX off
Apple Silicon). No model/GPU/server needed.

Run:  uv run python tests/test_backends.py
"""

import platform
import sys

sys.path.insert(0, ".")

import server.backends as be
from server.backends import Backend, _detect_backend, available_backends, make_engine

# --- detection from model id + platform ------------------------------------
assert _detect_backend("mlx-community/Qwen3.6-27B-4bit") == "mlx"
assert _detect_backend("TheBloke/Llama-2-7B-GGUF") == "llama_cpp"
assert _detect_backend("model.gguf") == "llama_cpp"
print("detect: OK")

# --- unknown backend -> ValueError naming the registry ---------------------
try:
    make_engine("whatever", backend="does-not-exist")
    raise AssertionError("unknown backend should raise")
except ValueError as e:
    assert "not available" in str(e), e
print("unknown backend: OK")


# --- registered but UNSUPPORTED here -> RuntimeError, and load() never runs --
def _boom() -> object:
    raise AssertionError("make_engine must not import an unsupported backend")


be.BACKENDS["faux"] = Backend(load=_boom, supported=lambda: False, requires="a GPU we lack")
try:
    make_engine("m", backend="faux")
    raise AssertionError("unsupported backend should raise")
except RuntimeError as e:
    assert "this host is" in str(e), e
finally:
    be.BACKENDS.pop("faux", None)
print("unsupported backend (no import): OK")

# --- registered + supported -> load() runs and constructs ------------------
_built: dict[str, str] = {}


def _fake_factory(model_id: str) -> object:
    _built["id"] = model_id
    return object()


be.BACKENDS["faux2"] = Backend(load=lambda: _fake_factory, supported=lambda: True, requires="")
try:
    eng = make_engine("the-model", backend="faux2")
    assert eng is not None and _built["id"] == "the-model"
finally:
    be.BACKENDS.pop("faux2", None)
print("supported backend builds: OK")

# --- mlx is registered; available iff this host is Apple Silicon -----------
assert "mlx" in be.BACKENDS
on_apple = platform.system() == "Darwin" and platform.machine() == "arm64"
assert ("mlx" in available_backends()) == on_apple
print(f"platform routing (apple_silicon={on_apple}): OK")

print("all backend tests passed")
