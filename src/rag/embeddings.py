import logging
from typing import List
import numpy as np
from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Provides embeddings for RAG chunk indexing and query matching.
    Supports local Hugging Face sentence-transformers or OpenAI API embeddings.
    """

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        self.model_name = settings.EMBEDDING_MODEL
        self._hf_model = None

    def _get_hf_model(self):
        if self._hf_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading local SentenceTransformer model: %s", self.model_name)
                self._hf_model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning("Could not load sentence_transformers: %s. Using fallback vectorizer.", str(e))
                self._hf_model = "fallback"
        return self._hf_model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of text strings into normalized float32 vectors."""
        if not texts:
            return np.empty((0, 384), dtype=np.float32)

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
                response = client.embeddings.create(
                    input=texts,
                    model=self.model_name if "embedding" in self.model_name else "text-embedding-3-small"
                )
                embeddings = [item.embedding for item in response.data]
                vecs = np.array(embeddings, dtype=np.float32)
                # Normalize for cosine similarity
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                return vecs / np.maximum(norms, 1e-9)
            except Exception as e:
                logger.error("OpenAI embedding failed: %s. Falling back to sentence-transformers.", str(e))

        # Sentence-transformers path
        hf = self._get_hf_model()
        if hf != "fallback":
            embeddings = hf.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings.astype(np.float32)

        # Deterministic lightweight fallback (e.g. for CI/offline testing without models downloaded)
        dimension = 384
        vectors = []
        for text in texts:
            np.random.seed(abs(hash(text)) % (2**32))
            v = np.random.randn(dimension).astype(np.float32)
            v /= np.linalg.norm(v)
            vectors.append(v)
        return np.array(vectors, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embeds a single query string into a 1D normalized vector."""
        vecs = self.embed_texts([query])
        return vecs[0]


embedding_service = EmbeddingService()

