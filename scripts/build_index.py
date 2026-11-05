import logging
from src.rag.ingest import ingest_documents
from src.rag.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("index_builder")

if __name__ == "__main__":
    logger.info("Starting offline FAISS vector index build...")
    count = ingest_documents()
    print(f"\n✅ FAISS Index build complete! Ingested {count} document chunks.")
    if vector_store.index:
        print(f"Total Vectors in FAISS Index: {vector_store.index.ntotal}")

