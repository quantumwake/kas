"""Zero-dependency embedder: signed feature hashing of tokens into a fixed-dim
vector, L2-normalised. No model, no network, no native deps — works on every
platform, fully offline. It's lexical (overlap-based), not semantic, so it's the
explicit floor (never auto-selected): a testing / air-gapped fallback so the
sqlite-vec pipeline always has *an* embedder.

Determinism matters: stored vectors must match query vectors across processes, so
it uses md5 (stable) rather than Python's per-process-salted hash().
"""

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9_]+")


def _hash(token: str) -> int:
    return int.from_bytes(hashlib.md5(token.encode("utf-8")).digest()[:8], "little")


class HashingEmbedder:
    name = "hashing"
    label = "hashing fallback (no model · lexical · low quality)"

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            h = _hash(tok)
            sign = 1.0 if (h >> 63) & 1 else -1.0
            vec[h % self.dim] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm:
            vec = [x / norm for x in vec]
        return vec
