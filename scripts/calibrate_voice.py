"""Interactive VAD calibration — supervised tuning of the voice endpoint.

Speak a sentence, pause when you're done; it shows what the detector decided
(when you started/stopped, how long after your pause it ended) + the transcript,
then you grade it. Your verdicts nudge the two knobs and it prints the settings
to keep:

  make calibrate-voice

  KAS_STT_SILENCE     pause (s) after speech that ends a turn   (the main knob)
  KAS_STT_VAD_THRESH  loudness (0..1) that counts as speech     (noise floor)

Grades: [y]es good · [e]arly (cut me off mid-thought) · [l]ate (waited too long)
        · [n] picked up noise / never ended · [q]uit.
"""

import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, ".")

from agent.adapters.audio.record import record  # noqa: E402
from agent.adapters.audio.stt import transcribe, whisper_available  # noqa: E402

MAX_SECS = 30


def one_round(hold: float, thresh: float) -> dict | None:
    """Record one VAD turn with the given knobs; return timing + transcript."""
    os.environ["KAS_STT_SILENCE"] = f"{hold}"
    os.environ["KAS_STT_VAD_THRESH"] = f"{thresh}"
    timeline: list[tuple[float, float]] = []
    ready = [None]  # wall-clock when the mic went hot ("speak now")

    def on_ready() -> None:
        ready[0] = time.monotonic()

    def on_level(level: float) -> None:
        timeline.append((time.monotonic(), level))

    wav = pathlib.Path(tempfile.mktemp(suffix=".wav"))
    t0 = time.monotonic()
    path, err = record(wav, MAX_SECS, on_ready=on_ready, on_level=on_level, vad=True)
    base = ready[0] or t0
    dur = time.monotonic() - base
    if err and path is None:
        return {"error": err}
    spoke = [(t - base, lv) for t, lv in timeline if lv >= thresh]
    text, terr = transcribe(path)
    try:
        path.unlink()
    except OSError:
        pass
    return {
        "dur": dur,
        "sp_start": spoke[0][0] if spoke else None,
        "sp_end": spoke[-1][0] if spoke else None,
        "tail": (dur - spoke[-1][0]) if spoke else None,
        "peak": max((lv for _, lv in timeline), default=0.0),
        "text": "" if terr else text,
    }


def main() -> int:
    if not whisper_available():
        print("calibration needs mlx-whisper (it transcribes each sample). /listen install")
        return 1
    hold = float(os.environ.get("KAS_STT_SILENCE", "2.5"))
    thresh = float(os.environ.get("KAS_STT_VAD_THRESH", "0.12"))
    goods: list[float] = []
    print(__doc__)
    print("Ctrl-C to quit at the prompt.\n")
    try:
        while True:
            input(f"[hold={hold:.1f}s thresh={thresh:.2f}]  Press Enter, then speak…")
            r = one_round(hold, thresh)
            if r is None or "error" in r:
                print(f"  recording error: {r.get('error') if r else 'unknown'}\n")
                continue
            if r["sp_end"] is None:
                print(f"  ⚠ no speech detected (peak level {r['peak']:.2f} < thresh {thresh:.2f})")
                if input("  lower threshold? [y/N] ").strip().lower() == "y":
                    thresh = max(0.03, round(thresh - 0.03, 2))
                print()
                continue
            near_max = r["dur"] >= MAX_SECS - 1
            print(
                f"  spoke {r['sp_start']:.1f}–{r['sp_end']:.1f}s  ·  "
                f"ended {r['tail']:.1f}s after you stopped"
                + ("  ⚠ ran to max — never found silence" if near_max else "")
            )
            print(f"  transcript: {r['text']!r}")
            ans = input("  grade [y/e/l/n/q]: ").strip().lower()
            if ans == "q":
                break
            if ans == "y":
                goods.append(hold)
            elif ans == "e":  # cut me off -> needs a longer pause to end
                hold = min(6.0, round(hold + 0.5, 1))
                print(f"  → raising hold to {hold:.1f}s")
            elif ans == "l":  # too slow -> shorter pause
                hold = max(0.5, round(hold - 0.5, 1))
                print(f"  → lowering hold to {hold:.1f}s")
            elif ans == "n":  # picked up noise -> raise the speech threshold
                thresh = min(0.6, round(thresh + 0.04, 2))
                print(f"  → raising threshold to {thresh:.2f}")
            print()
    except (KeyboardInterrupt, EOFError):
        print()
    best = (sum(goods) / len(goods)) if goods else hold
    print("\n── calibration result ─────────────────────────────")
    print(f"  KAS_STT_SILENCE={best:.1f}   KAS_STT_VAD_THRESH={thresh:.2f}")
    print(f"  keep it:  export KAS_STT_SILENCE={best:.1f} KAS_STT_VAD_THRESH={thresh:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
