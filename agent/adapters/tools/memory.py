"""Memory — the aggregator over pluggable recall backends (agent.ports.memory).

It owns the `recall` tool surface (hits formatted for the model, unchanged from
the old Recaller) and the introspection the /memory command renders (status +
in-TUI search). Backends are built lazily; today that's just Bm25Backend, but the
list is the single place a KgBackend / vector backend plugs in.
"""

import pathlib

from ...config import _truncate


def _human_bytes(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024 or unit == "GB":
            return f"{f:.0f} {unit}" if unit == "B" else f"{f:.1f} {unit}"
        f /= 1024
    return f"{f:.1f} GB"


class Memory:
    """Fans recall across MemoryBackends and renders their state for /memory."""

    def __init__(self, workdir: pathlib.Path) -> None:
        self.workdir = pathlib.Path(workdir)
        self._backends: list | None = None

    @property
    def backends(self) -> list:
        if self._backends is None:
            from ..retrieval.bm25 import Bm25Backend

            (self.workdir / ".agent").mkdir(parents=True, exist_ok=True)
            self._backends = [Bm25Backend(self.workdir)]
        return self._backends

    def refresh(self) -> None:
        for b in self.backends:
            try:
                b.refresh(self.workdir)
            except Exception:
                pass  # a broken backend must not take down recall

    def search(self, query: str, k: int = 8) -> list[dict]:
        """Raw fused hits across every backend (for the /memory search view)."""
        self.refresh()
        hits: list[dict] = []
        for b in self.backends:
            try:
                hits.extend(b.search(query, k))
            except Exception:
                pass
        # FTS5 bm25() scores are ascending (more negative = better); other
        # backends may differ, so sort each backend's own order is preserved by
        # a stable sort on score. Single backend today -> already ranked.
        hits.sort(key=lambda h: h.get("score", 0.0))
        return hits[:k]

    # -- the recall tool (model-facing; output unchanged from Recaller) -------

    def recall(self, query: str, k: int = 8) -> tuple[str, bool]:
        try:
            self.refresh()
        except Exception as exc:
            return f"recall index refresh failed: {type(exc).__name__}: {exc}", True
        hits = self.search(query, k=max(1, min(int(k or 8), 20)))
        if not hits:
            return f"no matches for {query!r} (try grep for exact strings)", False
        out = []
        for i, h in enumerate(hits, 1):
            snippet = h["body"] if len(h["body"]) < 600 else h["body"][:600] + "…"
            out.append(f"{i}. {h['path']}:{h['lines']} [{h['source']}]\n{snippet}")
        return _truncate("\n\n".join(out)), False

    # -- introspection for /memory -------------------------------------------

    def status_lines(self, recall_on: bool) -> list[tuple[str, str]]:
        """(text, style) rows describing every backend's indexed contents."""
        self.refresh()  # so the counts reflect reality, not a stale/empty index
        head = "ENABLED" if recall_on else "DISABLED (/memory on)"
        lines: list[tuple[str, str]] = [(f"memory  ·  recall {head}", "bold #ffb000")]
        for b in self.backends:
            try:
                st = b.stats()
            except Exception as exc:
                lines.append((f"  {b.name}: stats failed — {exc}", "red"))
                continue
            size = _human_bytes(st.get("size_bytes", 0))
            files = st.get("files", 0)
            lines.append(
                (f"  {st['name']}  —  {st.get('label', '')}", "yellow"),
            )
            lines.append((f"      {size}  ·  {files} files  ·  {st.get('path', '')}", "dim"))
            by_source = st.get("by_source") or {}
            if by_source:
                for src, n in sorted(by_source.items()):
                    lines.append((f"      {src:<8} {n} chunks", "yellow"))
            else:
                lines.append(("      (empty — nothing indexed yet)", "dim"))
        return lines

    def search_lines(self, query: str, k: int = 8) -> list[tuple[str, str]]:
        """(text, style) rows for an in-TUI `/memory search <query>`."""
        hits = self.search(query, k)
        if not hits:
            return [(f"memory search {query!r}  ·  no hits", "yellow")]
        lines = [(f"memory search {query!r}  ·  {len(hits)} hit(s)", "bold #ffb000")]
        for i, h in enumerate(hits, 1):
            tag = f"{h.get('source', '?')}·{h.get('backend', '?')}"
            lines.append((f"  {i}. {h['path']}:{h['lines']}  [{tag}]", "yellow"))
            snippet = " ".join(h["body"].split())[:140]
            lines.append((f"     {snippet}", "dim"))
        return lines
