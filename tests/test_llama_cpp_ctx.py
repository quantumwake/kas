"""Unit tests for llama.cpp GGUF metadata parsing + context sizing — no model
load, no GPU. Exercises the binary header reader that drives context-window
sizing (incl. the array-skip path) and the KAS_CTX / KAS_CTX_MAX precedence.

Run:  uv run python tests/test_llama_cpp_ctx.py
"""

import os
import struct
import sys
import tempfile

sys.path.insert(0, ".")

from server.backends.llama_cpp import LlamaCppEngine, _gguf_meta_int


def _s(x: str) -> bytes:
    b = x.encode()
    return struct.pack("<Q", len(b)) + b


def _build_gguf(path: str, ctx: int = 4096, with_array: bool = True) -> None:
    """A minimal valid GGUF header: architecture, an optional big array kv (to
    exercise skip()), and the context_length we want to read back."""
    kvs = [_s("general.architecture") + struct.pack("<I", 8) + _s("llama")]
    if with_array:
        # tokenizer.ggml.tokens: array(elem-type=8 string) of 3 — must be SKIPPED
        # without confusing the parser, since real context_length follows it.
        arr = struct.pack("<I", 9) + struct.pack("<I", 8) + struct.pack("<Q", 3)
        arr += _s("a") + _s("bb") + _s("ccc")
        kvs.append(_s("tokenizer.ggml.tokens") + arr)
    kvs.append(_s("llama.context_length") + struct.pack("<I", 4) + struct.pack("<I", ctx))
    body = b"GGUF" + struct.pack("<I", 3) + struct.pack("<Q", 0) + struct.pack("<Q", len(kvs))
    with open(path, "wb") as f:
        f.write(body + b"".join(kvs))


with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "m.gguf")

    # reads context_length by suffix, even with a preceding array to skip
    _build_gguf(p, ctx=4096, with_array=True)
    assert _gguf_meta_int(p, ".context_length") == 4096, _gguf_meta_int(p, ".context_length")
    _build_gguf(p, ctx=262144, with_array=True)
    assert _gguf_meta_int(p, ".context_length") == 262144

    # absent key and a non-GGUF file both return 0 (no crash)
    assert _gguf_meta_int(p, ".nope") == 0
    with open(p, "wb") as f:
        f.write(b"NOTGGUF and some bytes")
    assert _gguf_meta_int(p, ".context_length") == 0
    assert _gguf_meta_int(os.path.join(d, "missing.gguf"), ".context_length") == 0

# _choose_ctx is pure w.r.t. self (only logs) — exercise it on a bare instance.
eng = LlamaCppEngine.__new__(LlamaCppEngine)

# KAS_CTX overrides everything
os.environ["KAS_CTX"] = "9999"
try:
    assert eng._choose_ctx({"model_path": "/does/not/exist.gguf"}) == 9999
finally:
    del os.environ["KAS_CTX"]

# otherwise n_ctx = min(trained, KAS_CTX_MAX)
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "m.gguf")
    _build_gguf(p, ctx=262144)
    os.environ["KAS_CTX_MAX"] = "32768"
    try:
        assert eng._choose_ctx({"model_path": p}) == 32768  # cap below trained -> cap
    finally:
        del os.environ["KAS_CTX_MAX"]
    os.environ["KAS_CTX_MAX"] = "1000000"
    try:
        assert eng._choose_ctx({"model_path": p}) == 262144  # trained below cap -> trained
    finally:
        del os.environ["KAS_CTX_MAX"]

print("llama_cpp ctx/metadata tests passed")
