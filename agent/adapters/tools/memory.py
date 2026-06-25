"""Memory — the aggregator over pluggable recall backends (agent.ports.memory).

It owns the `recall` tool surface (hits formatted for the model, fused across
backends via RRF) and the introspection the /memory command renders (status +
in-TUI search). The ACTIVE backends are the enabled (persisted) ∩ installed stores
from the registry (agent.adapters.retrieval.stores) — built lazily here.
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
        self._instances: dict = {}  # name -> backend instance (lazy)

    def _instance(self, name: str):
        if name not in self._instances:
            from ..retrieval.stores import STORES

            (self.workdir / ".agent").mkdir(parents=True, exist_ok=True)
            self._instances[name] = STORES[name].build(self.workdir)
        return self._instances[name]

    @property
    def backends(self) -> list:
        """The ACTIVE backends: enabled (persisted) ∩ installed on this host."""
        from ..retrieval.stores import STORES, enabled_stores

        en = enabled_stores()
        return [self._instance(n) for n, spec in STORES.items() if n in en and spec.installed()]

    def refresh(self) -> None:
        for b in self.backends:
            try:
                b.refresh(self.workdir)
            except Exception:
                pass  # a broken backend must not take down recall

    def search(self, query: str, k: int = 8) -> list[dict]:
        """Fused hits across every backend via reciprocal-rank fusion.

        Backend scores aren't comparable (FTS5 bm25() is negative-ascending,
        vector distance is ~0..2), so we fuse by RANK not score: each hit
        contributes 1/(K+rank) to its (path,lines) slot, summed across backends.
        Single backend -> RRF is monotonic with rank, so order is unchanged."""
        self.refresh()
        K = 60
        fused: dict = {}
        for b in self.backends:
            try:
                hits = b.search(query, k)
            except Exception:
                hits = []
            for rank, h in enumerate(hits):
                slot = fused.setdefault(
                    (h.get("path"), h.get("lines")),
                    {"hit": h, "rrf": 0.0, "backends": set()},
                )
                slot["rrf"] += 1.0 / (K + rank + 1)
                slot["backends"].add(h.get("backend"))
        ranked = sorted(fused.values(), key=lambda s: s["rrf"], reverse=True)
        out = []
        for s in ranked[:k]:
            h = dict(s["hit"])
            h["rrf"] = s["rrf"]
            h["backends"] = sorted(x for x in s["backends"] if x)
            out.append(h)
        return out

    def reindex_lines(self, full: bool = False) -> list[tuple[str, str]]:
        """Reindex the active stores. full=True wipes each first (rebuild from
        scratch — e.g. after an embedder swap); else it's an incremental rescan."""
        actives = self.backends
        if not actives:
            return [("memory: no active stores to reindex (/memory enable <store>)", "yellow")]
        verb = "full rebuild" if full else "reindex (incremental)"
        lines: list[tuple[str, str]] = [(f"memory  ·  {verb}", "bold #ffb000")]
        for b in actives:
            try:
                if full and hasattr(b, "reset"):
                    b.reset()
                n = b.refresh(self.workdir)
                lines.append((f"  {b.name}: {n} file(s) indexed", "yellow"))
            except Exception as exc:
                lines.append((f"  {b.name}: failed — {type(exc).__name__}: {exc}", "red"))
        return lines

    def clear_lines(self) -> list[tuple[str, str]]:
        """Wipe every active store's index, leaving them empty (rebuild on demand)."""
        actives = self.backends
        if not actives:
            return [("memory: no active stores to clear", "yellow")]
        lines: list[tuple[str, str]] = [("memory  ·  cleared", "bold #ffb000")]
        for b in actives:
            if hasattr(b, "reset"):
                try:
                    b.reset()
                    lines.append((f"  {b.name}: index dropped", "yellow"))
                except Exception as exc:
                    lines.append((f"  {b.name}: clear failed — {exc}", "red"))
            else:
                lines.append((f"  {b.name}: no index to clear", "dim"))
        return lines

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
        """(text, style) rows: recall state, every store's platform/install/enabled
        state (with indexed counts when active), and embedder availability."""
        from ..embeddings import REGISTRY as EMB
        from ..retrieval.stores import EMBEDDER_BUNDLE, INSTALLS, STORES, enabled_stores

        self.refresh()  # active backends only -> counts reflect reality
        en = enabled_stores()
        head = "ENABLED" if recall_on else "DISABLED (/memory on)"
        lines: list[tuple[str, str]] = [(f"memory  ·  recall {head}", "bold #ffb000")]

        for name, spec in STORES.items():
            if not spec.supported():
                lines.append((f"  ✗ {name} — not supported on this OS/arch", "dim"))
            elif not spec.installed():
                note = INSTALLS[name].note if name in INSTALLS else ""
                lines.append(
                    (f"  ⤓ {name} — available, not installed · /memory install {name}", "yellow")
                )
                if note:
                    lines.append((f"      {note}", "dim"))
            else:
                active = name in en
                mark, hint = ("●", "") if active else ("○", f"  · /memory enable {name}")
                inst = self._instance(name)
                try:
                    st = inst.stats()
                except Exception as exc:
                    lines.append((f"  {mark} {name} — stats failed: {exc}", "red"))
                    continue
                lines.append((f"  {mark} {name} — {st.get('label', spec.label)}{hint}", "yellow"))
                if active:
                    size, files = _human_bytes(st.get("size_bytes", 0)), st.get("files", 0)
                    lines.append((f"      {size} · {files} files", "dim"))
                    for src, n in sorted((st.get("by_source") or {}).items()):
                        lines.append((f"      {src:<8} {n} chunks", "yellow"))

        # which embedders the vector store could use here (platform-filtered)
        embs = []
        for n, spec in sorted(EMB.items(), key=lambda kv: kv[1].priority):
            if n == "hashing":
                continue
            if not spec.supported():
                continue  # hide runtimes this OS/arch can't run
            bundle = EMBEDDER_BUNDLE.get(n, n)
            state = "installed" if spec.installed() else f"install: /memory install {bundle}"
            embs.append(f"{n} ({state})")
        if embs:
            lines.append((f"  embedders:  {'  ·  '.join(embs)}", "dim"))
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
