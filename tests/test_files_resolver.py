"""Characterization tests for PathResolver — the file-tool sandbox policy.

Locks behaviour before the v3 refactors. Notably it pins the *verified* property
that a symlink escaping the workdir is REJECTED (resolve() canonicalises the
symlink, then checks containment) — the finding the original report got backwards.
No model or server needed.

Run:  uv run python tests/test_files_resolver.py
"""

import os
import pathlib
import sys
import tempfile

sys.path.insert(0, ".")

from agent.adapters.tools.files import PathResolver, SandboxViolation


def _resolver(sandbox: bool) -> tuple[pathlib.Path, pathlib.Path, PathResolver]:
    tmp = pathlib.Path(tempfile.mkdtemp())
    work = tmp / "work"
    work.mkdir()
    return tmp, work, PathResolver(work, sandbox=sandbox)


# --- sandbox OFF: historical pass-through ----------------------------------
_tmp, work, r = _resolver(sandbox=False)
assert r.resolve("a.txt") == work / "a.txt"  # relative joins the workdir
assert r.resolve("/etc/hosts") == pathlib.Path("/etc/hosts")  # absolute untouched
print("sandbox off: OK")

# --- sandbox ON: inside allowed, escapes rejected --------------------------
_tmp, work, r = _resolver(sandbox=True)
assert r.resolve("sub/a.txt") == (work / "sub/a.txt").resolve()  # inside -> allowed
assert r.resolve(str(work)) == work.resolve()  # the root itself -> allowed
for bad in ("../escape.txt", "../../etc/hosts", "/etc/hosts"):
    try:
        r.resolve(bad)
        raise AssertionError(f"{bad!r} should be rejected")
    except SandboxViolation:
        pass
print("sandbox jail: OK")

# --- symlink escape is REJECTED (the corrected finding) --------------------
tmp, work, r = _resolver(sandbox=True)
secret = tmp / "secret"
secret.mkdir()
(secret / "f.txt").write_text("TOPSECRET")
os.symlink(secret, work / "link")  # workdir/link -> outside
try:
    r.resolve("link/f.txt")
    raise AssertionError("a symlink escaping the workdir must be rejected")
except SandboxViolation:
    pass
# a symlink that stays inside the workdir is fine
(work / "real.txt").write_text("ok")
os.symlink(work / "real.txt", work / "inside_link")
assert r.resolve("inside_link") == (work / "inside_link").resolve()
print("symlink escape rejected / inside symlink allowed: OK")

print("all files-resolver tests passed")
