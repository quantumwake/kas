"""Voice→text adapter: ffmpeg record-command construction and transcription
gating. No mic or model — the interactive capture/transcribe paths are mocked.

Run:  uv run python tests/test_audio.py
"""

import sys

sys.path.insert(0, ".")

from agent.adapters.audio import record as rec
from agent.adapters.audio import stt

# record_command: 16 kHz mono, time-limited, platform input format.
cmd = rec.record_command("/tmp/x.wav", 5)
if cmd is not None:  # None only on an unknown OS
    assert cmd[0] == "ffmpeg" and "/tmp/x.wav" in cmd
    assert "-ar" in cmd and cmd[cmd.index("-ar") + 1] == "16000"
    assert "-ac" in cmd and cmd[cmd.index("-ac") + 1] == "1"
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "5"
    assert any(f in cmd for f in ("avfoundation", "pulse"))
print("record_command: OK")

# record() degrades when ffmpeg is missing (simulate via PATH lookup miss).
orig_which = rec.shutil.which
rec.shutil.which = lambda _name: None
try:
    path, err = rec.record("/tmp/x.wav", 1)
    assert path is None and "ffmpeg" in err, (path, err)
finally:
    rec.shutil.which = orig_which
print("record ffmpeg-missing: OK")


# transcribe(): missing mlx-whisper -> graceful error, not a raise.
if not stt.whisper_available():
    text, is_err = stt.transcribe("/nonexistent.wav")
    assert is_err and "mlx-whisper" in text, (text, is_err)
    print("transcribe missing-dep: OK")
else:
    # Installed: a missing file is reported, still no raise.
    text, is_err = stt.transcribe("/definitely/not/here.wav")
    assert is_err and "no audio file" in text, (text, is_err)
    print("transcribe missing-file: OK")

# A successful transcription is plumbed through (mock mlx_whisper).
import types  # noqa: E402

fake = types.SimpleNamespace(
    transcribe=lambda path, path_or_hf_repo=None: {"text": "  hello world "}
)
sys.modules["mlx_whisper"] = fake
stt.importlib.util.find_spec = lambda name: object() if name == "mlx_whisper" else None
import tempfile  # noqa: E402

wav = tempfile.mktemp(suffix=".wav")
open(wav, "wb").close()
text, is_err = stt.transcribe(wav)
assert not is_err and text == "hello world", (text, is_err)
print("transcribe success (mocked): OK")

print("all audio tests passed")
