"""mlx-whisper in a CLEAN, isolated, LONG-LIVED subprocess: it loads the model
ONCE and transcribes many clips, so /listen never pays the model-load cost twice
(the Transcriber manager owns one of these per session).

Isolation matters: spawning whisper from inside the TUI's worker thread inherits
Textual's std fds and dies with "bad value(s) in fds_to_keep" when whisper (or a
dep) forks. A fresh process sidesteps that; a persistent one also stays warm.

  python -m agent.adapters.audio._transcribe_worker --serve <model>
      (then write one wav path per line on stdin)

Streams newline-delimited JSON on stdout:
  {"event":"loading","model":...} {"event":"ready"}   (model loaded; send paths)
  {"event":"transcribing","audio_secs":5.0}
  {"event":"done","text":"..."}  |  {"event":"error","msg":<traceback>}
"""

import json
import pathlib
import sys


def _emit(**d) -> None:
    sys.stdout.write(json.dumps(d) + "\n")
    sys.stdout.flush()


def _transcribe_one(wav: str, model: str) -> None:
    from .stt import _load_wav_16k_mono

    audio = _load_wav_16k_mono(pathlib.Path(wav))
    if audio is None:
        _emit(event="error", msg="unsupported audio format (need a PCM WAV)")
        return
    if len(audio) == 0:
        _emit(event="error", msg="no audio captured (check mic permission)")
        return
    import mlx_whisper

    _emit(event="transcribing", audio_secs=round(len(audio) / 16000, 1))
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=model)
    _emit(event="done", text=(result.get("text") or "").strip())


def _serve(model: str) -> int:
    """Load the model once (warm it on a short silent buffer), then transcribe a
    wav path per stdin line until EOF. mlx-whisper caches the loaded model, so
    every subsequent clip skips the load."""
    try:
        import mlx_whisper
        import numpy as np

        _emit(event="loading", model=model)
        mlx_whisper.transcribe(np.zeros(16000, dtype=np.float32), path_or_hf_repo=model)
        _emit(event="ready")
    except Exception:
        import traceback

        _emit(event="error", msg=traceback.format_exc())
        return 1
    for line in sys.stdin:
        wav = line.strip()
        if not wav:
            continue
        try:
            _transcribe_one(wav, model)
        except Exception:
            import traceback

            _emit(event="error", msg=traceback.format_exc())
    return 0


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 2 or args[0] != "--serve":
        _emit(event="error", msg="usage: _transcribe_worker --serve <model>")
        return 2
    return _serve(args[1])


if __name__ == "__main__":
    sys.exit(main())
