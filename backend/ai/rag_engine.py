"""
RAG engine — Phase 2.

Collections:
  medical_protocols  — IMGS, Ship Captain's Medical Guide chunks
  engine_manuals     — MAN B&W, Caterpillar, and vessel-specific manual chunks

Embeddings: sentence-transformers/all-MiniLM-L6-v2 (CPU-only)
Vector store: ChromaDB (persistent local, backend/data/chroma/)
"""
import os
from typing import List
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

_CHROMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma")

class RAGEngine:
    def __init__(self):
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=_CHROMA_DIR)
        self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    def query(self, collection_name: str, text: str, k: int = 5) -> List[dict]:
        """Return top-k relevant chunks from ChromaDB."""
        try:
            collection = self.client.get_collection(
                name=collection_name, 
                embedding_function=self.embedding_fn
            )
        except Exception:
            # Collection doesn't exist yet, return empty
            return []

        results = collection.query(
            query_texts=[text],
            n_results=k
        )
        
        chunks = []
        if results and results["documents"] and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            for doc, meta in zip(docs, metadatas):
                chunks.append({
                    "text": doc,
                    "metadata": meta
                })
        return chunks

    def add_documents(self, collection_name: str, documents: List[str], metadatas: List[dict], ids: List[str]):
        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
