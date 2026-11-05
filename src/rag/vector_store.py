import os
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from config.settings import settings
from src.rag.embeddings import embedding_service

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """
    Local FAISS vector store that maps dense semantic embeddings to document chunks
    and metadata for the Business Insights Copilot RAG Agent.
    """

    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = index_dir or settings.FAISS_INDEX_DIR
        self.index_path = self.index_dir / "index.faiss"
        self.meta_path = self.index_dir / "metadata.pkl"
        self.index: Optional[faiss.Index] = None
        self.chunks_metadata: List[Dict[str, Any]] = []

    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        Creates a new FAISS index from text chunks and saves it to disk.
        Each chunk is a dict with 'content', 'source', 'chunk_id', etc.
        """
        if not chunks:
            logger.warning("No chunks provided to build index.")
            return

        texts = [c["content"] for c in chunks]
        logger.info("Generating embeddings for %d chunks...", len(texts))
        vectors = embedding_service.embed_texts(texts)
        dimension = vectors.shape[1]

        # Use Inner Product (IndexFlatIP) on normalized vectors for exact Cosine Similarity
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(vectors)
        self.chunks_metadata = chunks

        self.save()
        logger.info("Built and saved FAISS index with %d vectors (dimension: %d).", self.index.ntotal, dimension)

    def save(self):
        """Persists FAISS index binary and chunk metadata pickle."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.chunks_metadata, f)
        logger.info("Saved index to %s and metadata to %s", self.index_path, self.meta_path)

    def load(self) -> bool:
        """Loads FAISS index and metadata from disk if available."""
        if not self.index_path.exists() or not self.meta_path.exists():
            logger.info("FAISS index files not found at %s. Empty index loaded.", self.index_dir)
            return False

        try:
            self.index = faiss.read_index(str(self.index_path))
            with open(self.meta_path, "rb") as f:
                self.chunks_metadata = pickle.load(f)
            logger.info("Successfully loaded FAISS index (%d items).", self.index.ntotal)
            return True
        except Exception as e:
            logger.error("Failed to load FAISS index: %s", str(e))
            return False

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Embeds the incoming query and retrieves the top-k most semantically relevant chunks.
        Returns a list of dicts with chunk content, source file, score, and chunk id.
        """
        if self.index is None or self.index.ntotal == 0:
            if not self.load():
                logger.warning("No FAISS index available to search.")
                return []

        query_vec = embedding_service.embed_query(query)
        query_mat = np.array([query_vec], dtype=np.float32)

        k = min(top_k, self.index.ntotal)
        if k == 0:
            return []

        scores, indices = self.index.search(query_mat, k)
        results = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.chunks_metadata):
                continue
            meta = self.chunks_metadata[idx]
            results.append({
                "content": meta["content"],
                "source": meta.get("source", "Unknown Document"),
                "chunk_id": meta.get("chunk_id", idx),
                "score": float(score)
            })

        return results


# Global singleton instance
vector_store = FAISSVectorStore()

