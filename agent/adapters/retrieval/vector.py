"""Semantic recall backend: sqlite-vec KNN over embedded chunks.

Conforms to agent.ports.memory.MemoryBackend. It reuses the same chunk walk as
BM25 (iter_workspace_chunks / iter_memory_chunks) but stores a vector per chunk in
a sqlite-vec vec0 table, embedded by whatever the embedder registry selected.

Both halves are optional and self-reporting: if `sqlite-vec` isn't installed or no
embedder is available, the backend is simply "unavailable" — refresh/search no-op
and stats() says how to enable it. So adding it to the aggregator never breaks
recall; it just lights up when the [memory] extra is present.

The embedder identity (name + dim) is stamped in a meta table; if it changes
(different model/dim), the vector store is rebuilt rather than mixing geometries.
"""

import importlib.util
import pathlib

from .bm25 import iter_memory_chunks, iter_workspace_chunks


class VectorBackend:
    name = "vector"

    def __init__(self, workdir: pathlib.Path, embedder=None) -> None:
        self.workdir = pathlib.Path(workdir)
        self.db_path = self.workdir / ".agent" / "vec.db"
        self._embedder = embedder  # injected (tests) or lazily selected
        self._embedder_resolved = embedder is not None
        self._db = None

    # -- availability ---------------------------------------------------------

    @property
    def embedder(self):
        if not self._embedder_resolved:
            from ..embeddings import make_embedder

            self._embedder = make_embedder()
            self._embedder_resolved = True
        return self._embedder

    def available(self) -> bool:
        return importlib.util.find_spec("sqlite_vec") is not None and self.embedder is not None

    # -- store ----------------------------------------------------------------

    def _connect(self):
        if self._db is not None:
            return self._db
        import sqlite3

        import sqlite_vec

        emb = self.embedder
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(str(self.db_path))
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, hash TEXT)")
        db.execute(
            "CREATE TABLE IF NOT EXISTS chunks("
            "id INTEGER PRIMARY KEY, path TEXT, lines TEXT, source TEXT, body TEXT)"
        )
        # rebuild if the embedder geometry changed (model/dim) — don't mix spaces
        want = f"{emb.name}:{emb.dim}"
        have = db.execute("SELECT value FROM meta WHERE key='embedder'").fetchone()
        if have and have[0] != want:
            db.execute("DROP TABLE IF EXISTS vec")
            db.execute("DELETE FROM files")
            db.execute("DELETE FROM chunks")
        db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec USING vec0(embedding float[{emb.dim}])")
        db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('embedder', ?)", (want,))
        db.commit()
        self._db = db
        return db

    def refresh(self, root: pathlib.Path) -> int:
        if not self.available():
            return 0
        import sqlite_vec

        db = self._connect()
        emb = self.embedder
        n = 0
        for it in (iter_workspace_chunks(root), iter_memory_chunks(root)):
            for key, source, digest, chunks in it:
                row = db.execute("SELECT hash FROM files WHERE path = ?", (key,)).fetchone()
                if row and row[0] == digest:
                    continue  # unchanged
                for (cid,) in db.execute("SELECT id FROM chunks WHERE path = ?", (key,)).fetchall():
                    db.execute("DELETE FROM vec WHERE rowid = ?", (cid,))
                db.execute("DELETE FROM chunks WHERE path = ?", (key,))
                if chunks:
                    vecs = emb.embed([body for _, _, body in chunks])
                    for (a, b, body), v in zip(chunks, vecs, strict=True):
                        cur = db.execute(
                            "INSERT INTO chunks(path, lines, source, body) VALUES (?, ?, ?, ?)",
                            (key, f"{a}-{b}", source, body),
                        )
                        db.execute(
                            "INSERT INTO vec(rowid, embedding) VALUES (?, ?)",
                            (cur.lastrowid, sqlite_vec.serialize_float32(v)),
                        )
                db.execute("INSERT OR REPLACE INTO files(path, hash) VALUES (?, ?)", (key, digest))
                n += 1
        db.commit()
        return n

    def search(self, query: str, k: int = 8) -> list[dict]:
        if not self.available():
            return []
        import sqlite_vec

        db = self._connect()
        qv = self.embedder.embed([query])[0]
        rows = db.execute(
            "SELECT c.body, c.path, c.lines, c.source, v.distance "
            "FROM vec v JOIN chunks c ON c.id = v.rowid "
            "WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
            (sqlite_vec.serialize_float32(qv), max(1, min(int(k or 8), 20))),
        ).fetchall()
        return [
            {
                "body": b,
                "path": p,
                "lines": ln,
                "source": s,
                "score": float(d),
                "backend": self.name,
            }
            for b, p, ln, s, d in rows
        ]

    def stats(self) -> dict:
        info: dict = {"name": self.name, "path": str(self.db_path)}
        if not self.available():
            why = "install the [memory] extra (sqlite-vec + an embedder)"
            info.update(
                label=f"vector — unavailable: {why}",
                by_source={},
                files=0,
                size_bytes=0,
                unavailable=True,
            )
            return info
        db = self._connect()
        by_source = dict(
            db.execute("SELECT source, COUNT(*) FROM chunks GROUP BY source").fetchall()
        )
        files = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        size = self.db_path.stat().st_size if self.db_path.exists() else 0
        emb = self.embedder
        info.update(
            label=f"vector (sqlite-vec · {emb.name} · dim {emb.dim})",
            by_source=by_source,
            files=files,
            size_bytes=size,
        )
        return info
