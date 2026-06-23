"""Characterization tests for the bash adapter: clean_terminal() output
cleaning and the BashSession PTY lifecycle (exit capture, idle detection, kill).
Uses trivial shell commands — no model or server needed.

Run:  uv run python tests/test_bash.py
"""

import pathlib
import sys
import tempfile

sys.path.insert(0, ".")

from agent.adapters.tools.bash import BashSession, clean_terminal

# --- clean_terminal: ANSI strip + carriage-return overwrite ----------------
assert clean_terminal("\x1b[31mred\x1b[0m") == "red"  # color codes stripped
assert clean_terminal("a\rb") == "b"  # lone \r = overwrite, keep last segment
assert clean_terminal("x\r\ny") == "x\ny"  # CRLF -> LF, not an overwrite
assert clean_terminal("a\n\n\n\nb") == "a\n\nb"  # 3+ blank lines collapsed
print("clean_terminal: OK")

work = pathlib.Path(tempfile.mkdtemp())

# --- a command that exits: output captured, status "exited" ----------------
s = BashSession(r"printf 'hello\n'", work)
out, status = s.read_until_idle()
assert status == "exited", status
assert "hello" in out, repr(out)
assert not s.alive()
s.close()
print("exit capture: OK")

# --- a command that waits for input: status "waiting" ----------------------
_saved = BashSession.IDLE_TIMEOUT
BashSession.IDLE_TIMEOUT = 0.3  # speed the idle detection up for the test
try:
    s = BashSession("cat", work)  # cat blocks on stdin -> goes idle
    assert s.alive()
    out, status = s.read_until_idle()
    assert status == "waiting", (status, repr(out))
    s.kill()
    assert not s.alive()
finally:
    BashSession.IDLE_TIMEOUT = _saved
print("idle/waiting + kill: OK")

print("all bash tests passed")
