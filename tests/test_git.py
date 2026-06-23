"""Characterization tests for GitWorkspace: the per-turn checkpoint policy.
Runs in a throwaway temp dir (outside any repo) so ready() takes the "init a
fresh repo" path. No model or server needed.

Run:  uv run python tests/test_git.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, ".")

from agent.adapters.workspace.git import GitWorkspace

# Make `git commit` work without relying on the machine's global git identity
# (CI runners have none). GitWorkspace inherits this process environment.
os.environ.setdefault("GIT_AUTHOR_NAME", "kas-test")
os.environ.setdefault("GIT_AUTHOR_EMAIL", "kas-test@example.com")
os.environ.setdefault("GIT_COMMITTER_NAME", "kas-test")
os.environ.setdefault("GIT_COMMITTER_EMAIL", "kas-test@example.com")


class FakeIO:
    def __init__(self) -> None:
        self.notices: list[str] = []

    def notice(self, msg: str) -> None:
        self.notices.append(msg)


tmp = pathlib.Path(tempfile.mkdtemp())
io = FakeIO()
gw = GitWorkspace(tmp, io)

# --- ready(): a fresh dir gets initialized as a workspace repo --------------
assert gw.ready() is True
assert (tmp / ".agent" / "workspace-repo").exists()  # marker written
assert (tmp / ".gitignore").exists()  # default gitignore written
assert any("workspace repo initialized" in n for n in io.notices), io.notices
print("ready/init: OK")

# --- checkpoint(): only mutating turns with real changes commit ------------
assert gw.checkpoint(False, "noop") is None  # not mutating -> no commit

(tmp / "file.py").write_text("print(1)\n")
sha = gw.checkpoint(True, "add file")
assert sha and len(sha) >= 4, sha  # a real change -> short sha
print(f"checkpoint commit: OK ({sha})")

# mutated flag set but nothing changed since the last commit -> None
assert gw.checkpoint(True, "again") is None
print("no-op checkpoint: OK")

# --- ready() is decided once (cached) --------------------------------------
assert gw.ready() is True
print("all git tests passed")
