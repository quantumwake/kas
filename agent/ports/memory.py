"""The memory / recall port: a pluggable retrieval backend the aggregator fans
queries across. Adapters: Bm25Backend (lexical, now), KgBackend (graph, later).

The aggregator (agent.adapters.tools.memory.Memory) owns the `recall` tool
surface and the introspection the /memory command renders; each backend only has
to index, search, and describe itself.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryBackend(Protocol):
    name: str  # short id, e.g. "bm25" / "kg" — also tags each hit's `backend`

    def refresh(self, root) -> int:
        """(Re)index from `root`; return the number of items (re)indexed. Cheap
        to call repeatedly — implementations skip unchanged inputs."""
        ...

    def search(self, query: str, k: int = 8) -> list[dict]:
        """Ranked hits. Each is a dict with at least: body, path, lines, source,
        score, backend."""
        ...

    def stats(self) -> dict:
        """Introspection for /memory: at least name, label, by_source (counts),
        and size_bytes. Backends may add their own fields."""
        ...
