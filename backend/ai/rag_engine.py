"""
RAG engine — Phase 2.

Collections:
  medical_protocols  — IMGS, Ship Captain's Medical Guide chunks
  engine_manuals     — MAN B&W, Caterpillar, and vessel-specific manual chunks

Embeddings: sentence-transformers/all-MiniLM-L6-v2 (CPU-only)
Vector store: ChromaDB (persistent local, backend/data/chroma/)
"""
from typing import List


class RAGEngine:
    def query(self, collection: str, text: str, k: int = 5) -> List[dict]:
        """Return top-k relevant chunks from ChromaDB. Phase 2 implementation."""
        raise NotImplementedError("RAG engine is Phase 2")
