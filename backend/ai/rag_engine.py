"""
RAG engine — SQLite FTS5 backend.

Drop-in replacement for the previous ChromaDB + sentence-transformers stack.
Same class name and method signatures so call sites in routers/ai.py and the
ingest scripts keep working unchanged.

Why FTS5 over embeddings:
  - SQLite FTS5 is built into stock Python — zero new dependencies, and we
    were already pulling in SQLite via SQLAlchemy.
  - BM25 ranking (built into FTS5) is competitive with embedding search on
    structured technical/medical documents where vocabulary is consistent.
  - Bundle size drops by ~1 GB (no torch, no transformers, no embedding model
    download on first launch). Makes the Tauri / PyInstaller path tractable.

Collections (same names as before):
  medical_protocols  — WHO IMGS, Ship Captain's Medical Guide chunks
  engine_manuals     — MAN B&W, Caterpillar, vessel-specific manual chunks

Data location:
  $VESSEL_OPS_DATA_DIR/knowledge.sqlite  (writable, per-install)
  backend/data/knowledge/*.json          (read-only, bundled with the app)

On first run, bundled JSON chunks are ingested into the SQLite FTS5 index.
After that the index is reused. Re-running the bundled ingest is idempotent
because chunk_ids are stable.
"""
import json
import os
import sqlite3
from typing import List, Dict, Any

from backend.rag.store import knowledge_store

_DATA_DIR = os.getenv(
    "VESSEL_OPS_DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
)
_DB_PATH = os.path.join(_DATA_DIR, "knowledge.sqlite")

_BUNDLED_CHUNKS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "knowledge")
)


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks USING fts5(
            collection,
            text,
            metadata,
            chunk_id UNINDEXED,
            tokenize = 'porter unicode61'
        )
        """
    )
    return conn


def _sanitize_fts5_query(text: str) -> str:
    """Convert free text into a safe FTS5 MATCH expression.

    FTS5 has its own query syntax (operators like AND/OR/NEAR, column filters,
    special chars). Passing raw user input causes SyntaxError. We strip to
    alphanumeric tokens of length >= 2, quote each, and OR them together so
    matches against any token still produce BM25-ranked results.
    """
    tokens = []
    for word in text.split():
        clean = "".join(c for c in word if c.isalnum())
        if len(clean) >= 2:
            tokens.append(f'"{clean}"')
    return " OR ".join(tokens) if tokens else '""'


class RAGEngine:
    def __init__(self):
        with _connect() as conn:
            conn.commit()
        self._bootstrap_from_bundled_chunks()

    def _bootstrap_from_bundled_chunks(self) -> None:
        """Ingest shipped JSON chunks into FTS5 if the index is empty.

        Bundled chunks live at backend/data/knowledge/*.json with the schema:
            {"collection": "medical_protocols",
             "chunks": [{"id": "...", "text": "...", "metadata": {...}}, ...]}
        """
        if not os.path.isdir(_BUNDLED_CHUNKS_DIR):
            return
        try:
            with _connect() as conn:
                existing = conn.execute("SELECT count(*) FROM rag_chunks").fetchone()[0]
            if existing > 0:
                return
        except sqlite3.OperationalError:
            return

        for filename in sorted(os.listdir(_BUNDLED_CHUNKS_DIR)):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(_BUNDLED_CHUNKS_DIR, filename)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.add_documents(
                    collection_name=data["collection"],
                    documents=[c["text"] for c in data["chunks"]],
                    metadatas=[c.get("metadata", {}) for c in data["chunks"]],
                    ids=[c["id"] for c in data["chunks"]],
                )
            except (json.JSONDecodeError, KeyError, IOError):
                # Skip malformed bundled files rather than crashing app boot.
                continue

    def query(self, collection_name: str, text: str, k: int = 5) -> List[Dict[str, Any]]:
        fts_query = _sanitize_fts5_query(text)
        chunks: List[Dict[str, Any]] = []
        try:
            with _connect() as conn:
                rows = conn.execute(
                    """
                    SELECT text, metadata
                    FROM rag_chunks
                    WHERE collection = ? AND rag_chunks MATCH ?
                    ORDER BY bm25(rag_chunks)
                    LIMIT ?
                    """,
                    (collection_name, fts_query, k),
                ).fetchall()
            for row in rows:
                try:
                    meta = json.loads(row["metadata"]) if row["metadata"] else {}
                except json.JSONDecodeError:
                    meta = {}
                chunks.append({"text": row["text"], "metadata": meta})
        except sqlite3.OperationalError:
            pass

        # Preserve the JSON KnowledgeStore fallback — same behavior as before so
        # uploads via /api/ai/upload-manual still surface in queries.
        if collection_name == "medical_protocols":
            extra = knowledge_store.search_protocols(text)
            if extra:
                chunks.append({"text": extra, "metadata": {"source": "Local JSON Protocols"}})
        elif collection_name == "engine_manuals":
            extra = knowledge_store.search_manuals(text)
            if extra:
                chunks.append({"text": extra, "metadata": {"source": "Local JSON Manuals"}})

        return chunks

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[dict],
        ids: List[str],
    ) -> None:
        with _connect() as conn:
            for doc, meta, chunk_id in zip(documents, metadatas, ids):
                # Upsert: delete-then-insert keeps re-ingests idempotent.
                conn.execute("DELETE FROM rag_chunks WHERE chunk_id = ?", (chunk_id,))
                conn.execute(
                    "INSERT INTO rag_chunks (collection, text, metadata, chunk_id) VALUES (?, ?, ?, ?)",
                    (collection_name, doc, json.dumps(meta or {}), chunk_id),
                )
            conn.commit()

    def collection_stats(self, collection_name: str) -> int:
        """Return the number of indexed chunks in a collection.

        Replaces the leaky `engine.client.get_collection(name).count()` call
        that exposed the underlying chromadb client to the router layer.
        """
        try:
            with _connect() as conn:
                row = conn.execute(
                    "SELECT count(*) FROM rag_chunks WHERE collection = ?",
                    (collection_name,),
                ).fetchone()
                return row[0] if row else 0
        except sqlite3.OperationalError:
            return 0
