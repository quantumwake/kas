"""MLX embedder: runs a real embedding model on Apple's MLX (Metal-accelerated on
Apple Silicon), offline. Best quality + speed on a Mac; Apple-only, so the
registry guards it behind _is_apple_silicon BEFORE this module is imported.

Targets the `mlx-embeddings` package (load + a sentence-transformers-style model
exposing pooled `text_embeds`). Model via KAS_EMBED_MODEL. The exact call shape
can vary by package version; adjust here, not at the call sites.
"""

import os


class MlxEmbedder:
    name = "mlx"

    def __init__(self, model: str | None = None) -> None:
        from mlx_embeddings.utils import load  # deferred + Apple-gated by the registry

        self.model_id = model or os.environ.get(
            "KAS_EMBED_MODEL", "mlx-community/all-MiniLM-L6-v2-bf16"
        )
        self._model, self._tok = load(self.model_id)
        self.label = f"MLX embeddings ({self.model_id})"
        self.dim = len(self.embed(["probe"])[0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        inputs = self._tok.batch_encode_plus(
            list(texts),
            return_tensors="mlx",
            padding=True,
            truncation=True,
            max_length=int(os.environ.get("KAS_EMBED_CTX", "512")),
        )
        out = self._model(inputs["input_ids"], attention_mask=inputs.get("attention_mask"))
        embeds = out.text_embeds  # (batch, dim) — pooled + normalised
        return [[float(x) for x in row] for row in embeds.tolist()]
