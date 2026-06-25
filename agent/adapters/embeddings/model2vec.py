"""model2vec embedder: distilled STATIC embeddings — numpy only, no torch, ~30MB,
CPU, cross-platform, offline after the first model pull. The portable default when
no GPU runtime is available.

Model via KAS_EMBED_MODEL (default minishlab/potion-base-8M). Import is deferred
so the package is only loaded when this embedder is actually selected.
"""

import os


class Model2VecEmbedder:
    name = "model2vec"

    def __init__(self, model: str | None = None) -> None:
        from model2vec import StaticModel  # deferred: only when selected

        self.model_id = model or os.environ.get("KAS_EMBED_MODEL", "minishlab/potion-base-8M")
        self._m = StaticModel.from_pretrained(self.model_id)
        self.label = f"model2vec static ({self.model_id})"
        self.dim = len(self.embed(["probe"])[0])  # probe to learn the dimensionality

    def embed(self, texts: list[str]) -> list[list[float]]:
        import numpy as np

        out = np.asarray(self._m.encode(list(texts)), dtype="float32")
        return [v.tolist() for v in out]
