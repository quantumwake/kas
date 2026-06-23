"""Tests for the "offer to start the server" flow added to the agent CLI:
the local-vs-remote / TTY gating and the accept/decline outcomes. The real
spawn + wait are stubbed so no process is launched. No model or server needed.

Run:  uv run python tests/test_server_start.py
"""

import builtins
import sys

sys.path.insert(0, ".")

import agent.cli as cli


class FakeStdin:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def offer(url, tty, answer, *, model=None, can_start=True, served=("served-model", 4096)):
    """Drive _offer_to_start_server with a controlled TTY, input, and a stubbed
    (never real) spawn/wait/probe."""
    saved = (
        sys.stdin,
        builtins.input,
        cli._spawn_server,
        cli._wait_for_server,
        cli.served_info,
    )
    sys.stdin = FakeStdin(tty)
    builtins.input = lambda *a: answer
    cli._spawn_server = lambda port, model=None: "fake-proc"
    cli._wait_for_server = lambda base, proc, attempts=180: can_start
    cli.served_info = lambda base: served
    try:
        return cli._offer_to_start_server(url, model)
    finally:
        sys.stdin, builtins.input = saved[0], saved[1]
        cli._spawn_server, cli._wait_for_server, cli.served_info = saved[2], saved[3], saved[4]


# --- _is_local_url ---------------------------------------------------------
assert cli._is_local_url("http://127.0.0.1:8765")
assert cli._is_local_url("http://localhost:9000")
assert not cli._is_local_url("http://example.com:8765")
assert not cli._is_local_url("https://api.remote.net")
print("is_local_url: OK")

# --- gating: never offer for a remote URL or a non-TTY ---------------------
assert offer("http://example.com:8765", True, "y") == (None, None)  # remote
assert offer("http://127.0.0.1:8765", False, "y") == (None, None)  # not a TTY
print("gating (remote / non-tty): OK")

# --- decline ---------------------------------------------------------------
assert offer("http://127.0.0.1:8765", True, "n") == (None, None)
assert offer("http://127.0.0.1:8765", True, "no") == (None, None)
print("decline: OK")

# --- accept: blank or yes -> starts and returns the server's model ---------
assert offer("http://127.0.0.1:8765", True, "") == ("served-model", 4096)  # Enter = default yes
assert offer("http://127.0.0.1:8765", True, "y") == ("served-model", 4096)
print("accept -> start: OK")

# --- accept but the server fails to come up -> (None, None) -----------------
assert offer("http://127.0.0.1:8765", True, "y", can_start=False) == (None, None)
print("accept but start fails: OK")

print("all server-start tests passed")
