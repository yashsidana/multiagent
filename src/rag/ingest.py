import logging
from pathlib import Path
from typing import List, Dict, Any
from config.settings import settings
from src.rag.vector_store import vector_store

logger = logging.getLogger(__name__)


class RecursiveTextSplitter:
    """
    Lightweight recursive text splitter that breaks down large documents
    into manageable chunks while preserving paragraph and sentence coherence.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n## ", "\n### ", "\n\n", "\n", ". ", " "]

    def split_text(self, text: str) -> List[str]:
        final_chunks: List[str] = []
        
        # Split by top separator first
        def _recursive_split(subtext: str, sep_idx: int) -> List[str]:
            if len(subtext) <= self.chunk_size:
                return [subtext.strip()] if subtext.strip() else []
            
            if sep_idx >= len(self.separators):
                # Hard character truncation if no separator fits
                return [subtext[i:i + self.chunk_size].strip() for i in range(0, len(subtext), self.chunk_size - self.chunk_overlap)]

            sep = self.separators[sep_idx]
            splits = subtext.split(sep)
            chunks: List[str] = []
            current = ""

            for part in splits:
                piece = part if not current else sep + part
                if len(current) + len(piece) <= self.chunk_size:
                    current += piece
                else:
                    if current.strip():
                        chunks.append(current.strip())
                    if len(part) > self.chunk_size:
                        subparts = _recursive_split(part, sep_idx + 1)
                        chunks.extend(subparts)
                        current = ""
                    else:
                        current = part

            if current.strip():
                chunks.append(current.strip())

            return chunks

        raw_chunks = _recursive_split(text, 0)
        
        # Apply sliding overlap across adjacent chunks
        for i, c in enumerate(raw_chunks):
            if i > 0 and self.chunk_overlap > 0:
                overlap_prefix = raw_chunks[i - 1][-self.chunk_overlap:]
                combined = f"{overlap_prefix} {c}".strip()
                final_chunks.append(combined)
            else:
                final_chunks.append(c)

        return final_chunks


def ingest_documents(documents_dir: Path = settings.DOCUMENTS_DIR) -> int:
    """
    Scans the documents directory, splits text files into chunks,
    and builds/persists the FAISS vector index.
    """
    if not documents_dir.exists():
        logger.warning("Documents directory %s does not exist. Creating it.", documents_dir)
        documents_dir.mkdir(parents=True, exist_ok=True)
        return 0

    all_chunks: List[Dict[str, Any]] = []
    splitter = RecursiveTextSplitter(chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)

    supported_extensions = [".md", ".txt", ".rst"]
    files = [f for f in documents_dir.glob("*") if f.suffix.lower() in supported_extensions]

    logger.info("Found %d documents to ingest from %s", len(files), documents_dir)

    chunk_counter = 0
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            file_chunks = splitter.split_text(content)
            for idx, c in enumerate(file_chunks):
                all_chunks.append({
                    "chunk_id": f"{file_path.stem}_{idx}",
                    "source": file_path.name,
                    "content": c,
                    "length": len(c)
                })
                chunk_counter += 1

        except Exception as e:
            logger.error("Error reading file %s: %s", file_path, str(e))

    if all_chunks:
        vector_store.build_index(all_chunks)
        logger.info("Successfully ingested %d chunks across %d documents.", len(all_chunks), len(files))
    else:
        logger.warning("No document chunks were generated.")

    return len(all_chunks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_documents()

