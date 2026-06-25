"""GGUF embedder via llama-cpp-python: a real transformer, cross-platform
(CPU / Metal / CUDA / ROCm depending on how llama-cpp-python was built), offline.
Heavier than model2vec but higher quality.

Needs a GGUF embedding model — set KAS_EMBED_MODEL to its path (e.g. a
nomic-embed-text or bge gguf). Import is deferred until selected.
"""

import os


class GgufEmbedder:
    name = "gguf"

    def __init__(self, model: str | None = None) -> None:
        from llama_cpp import Llama  # deferred: only when selected

        path = model or os.environ.get("KAS_EMBED_MODEL")
        if not path:
            raise RuntimeError("KAS_EMBED_MODEL must point to a GGUF embedding model")
        self._llm = Llama(
            model_path=path,
            embedding=True,
            verbose=False,
            n_ctx=int(os.environ.get("KAS_EMBED_CTX", "512")),
        )
        self.label = f"GGUF embeddings ({os.path.basename(path)})"
        self.dim = len(self.embed(["probe"])[0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = self._llm.create_embedding(list(texts))
        return [d["embedding"] for d in out["data"]]
