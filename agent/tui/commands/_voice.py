"""Shared voice-capture step for /listen and /converse: record (with the warmup
'speak now' cue and a live mic level feeding the fx voice meter), then transcribe
— driving the app's voice indicator through the phases. One place so the two
commands can't drift apart."""

import pathlib
import tempfile

from rich.text import Text

from ...adapters.audio.record import record
from ...adapters.audio.stt import transcribe


def note(app, msg: str, style: str) -> None:
    """Write a status line to the body from a worker thread (best-effort)."""
    try:
        app.call_from_thread(app.body_write, Text(msg, style=style))
    except Exception:
        try:
            app.body_write(Text(msg, style=style))
        except Exception:
            pass


def listen_once(app, max_secs: int, vad: bool = False) -> tuple[str, str]:
    """Record from the mic then transcribe. Returns (text, error) — error is ""
    on success. vad=True ends the turn on silence (conversation); vad=False
    records for max_secs (one-shot /listen)."""
    wav = pathlib.Path(tempfile.mktemp(suffix=".wav"))
    app.voice_indicator("listening", conn="🎙 warming mic", work="…")

    def cue() -> None:  # fired once the mic is actually hot
        app.voice_indicator("listening", conn="🔴 speak now", work="listening…")

    def on_level(level: float) -> None:  # drives the audio-reactive fx meter
        app.voice_level = level

    path, err = record(wav, max_secs, on_ready=cue, on_level=on_level, vad=vad)
    if err:
        app.voice_indicator(None)
        return "", err

    app.voice_indicator("transcribing", conn="🎧 transcribing", work="…")
    text, is_error = transcribe(path)
    app.voice_indicator(None)
    try:
        path.unlink()
    except OSError:
        pass
    return ("", text) if is_error else (text, "")
