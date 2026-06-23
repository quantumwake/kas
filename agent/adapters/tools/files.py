"""Filesystem access policy for the file tools.

PathResolver turns a tool's `path` argument into an absolute path. With
`sandbox=True` it jails every access to the workdir subtree, so a path that
resolves outside it (an absolute path, or a `../` escape — e.g. from
prompt-injected web content) is refused before it touches the host. Because
`.resolve()` canonicalises symlinks before the containment check, a symlink
inside the workdir pointing outside is also rejected. With `sandbox=False` it
preserves the historical behaviour: relative paths join the workdir, absolute
paths pass through untouched — the agent can read/write anywhere the user can.

As of v3 the CLI enables the sandbox by default (`--no-sandbox` / KAS_SANDBOX=0
to opt out); the class-level default stays `False` for programmatic callers.
"""

import pathlib


class SandboxViolation(Exception):
    """A file tool was asked to touch a path outside the sandbox."""


class PathResolver:
    def __init__(self, workdir: pathlib.Path, sandbox: bool = False) -> None:
        self.workdir = workdir
        self.sandbox = sandbox

    def resolve(self, path: str) -> pathlib.Path:
        p = pathlib.Path(path)
        full = p if p.is_absolute() else self.workdir / p
        if not self.sandbox:
            return full
        resolved = full.resolve()
        root = self.workdir.resolve()
        if resolved != root and not resolved.is_relative_to(root):
            raise SandboxViolation(
                f"path {path!r} resolves outside the sandbox ({root}); "
                "re-run with --no-sandbox to allow it"
            )
        return resolved
