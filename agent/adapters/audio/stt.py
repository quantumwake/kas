"""Speech→text via mlx-whisper (Apple Silicon).

mlx-whisper is an optional dep (`uv add mlx-whisper`). The model is a Whisper
checkpoint in MLX format — KAS_STT_MODEL overrides it; the default is a small,
fast turbo build pulled on first use. (The cached openai/whisper-* PyTorch
checkpoints aren't MLX-format, so point KAS_STT_MODEL at an mlx-community/whisper-*
repo or let the default download.) Everything here degrades gracefully: a missing
package or model returns an (error_message, True) pair rather than raising.
"""

import importlib.util
import os
import pathlib

DEFAULT_MODEL = os.environ.get("KAS_STT_MODEL", "mlx-community/whisper-large-v3-turbo")


def whisper_available() -> bool:
    return importlib.util.find_spec("mlx_whisper") is not None


def _missing_hint() -> str:
    return (
        "voice→text needs mlx-whisper — install it (`uv add mlx-whisper`) on Apple "
        "Silicon, then /listen again"
    )


def transcribe(audio_path: str | pathlib.Path, model: str | None = None) -> tuple[str, bool]:
    """Transcribe an audio file. Returns (text, is_error)."""
    if not whisper_available():
        return _missing_hint(), True
    p = pathlib.Path(audio_path)
    if not p.exists():
        return f"no audio file at {p}", True
    import mlx_whisper

    try:
        result = mlx_whisper.transcribe(str(p), path_or_hf_repo=model or DEFAULT_MODEL)
    except Exception as exc:  # model load / decode failures shouldn't crash the app
        return f"transcription failed: {type(exc).__name__}: {exc}", True
    return (result.get("text") or "").strip(), False
