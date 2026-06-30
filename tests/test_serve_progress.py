"""Unit tests for `kas serve` download/load progress tail parsing — the bit that
surfaces the daemon log's latest line (HF download %/speed, load messages) while
the server starts, so a multi-GB pull isn't an invisible freeze.

Run:  uv run python tests/test_serve_progress.py
"""

import os
import sys
import tempfile

sys.path.insert(0, ".")

from agent.cli import _log_tail

with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "server.log")

    # tqdm overwrites with \r; the latest fragment (after the final \n) wins
    with open(p, "w") as f:
        f.write("loading model\rfetch 10%\rfetch 55%\rfetch 100%\nloaded ok")
    assert _log_tail(p) == "loaded ok", _log_tail(p)

    # a live HF download bar is surfaced verbatim (carriage-return separated)
    with open(p, "w") as f:
        f.write("starting\rmodel.gguf 45%|####  | 8.1G/18.0G [01:23<01:42, 97MB/s]")
    tail = _log_tail(p)
    assert "45%" in tail and "MB/s" in tail, tail

    # empty file and a missing file both yield "" (no crash)
    open(p, "w").close()
    assert _log_tail(p) == ""
    assert _log_tail(os.path.join(d, "absent.log")) == ""

print("serve progress tail tests passed")
