import logging
from typing import List, Dict, Any
from config.settings import settings
from src.agents.state import CopilotState
from src.rag.vector_store import vector_store

logger = logging.getLogger(__name__)


def rag_agent_node(state: CopilotState) -> CopilotState:
    """
    LangGraph node: Retrieves relevant document chunks from the FAISS vector store
    and extracts source metadata for grounding the final answer.
    """
    question = state.get("question", "")
    logger.info("RAG Agent searching FAISS index for: %s", question)

    top_chunks = vector_store.search(question, top_k=settings.RETRIEVAL_TOP_K)

    context_snippets: List[str] = []
    sources: List[Dict[str, Any]] = []

    for idx, c in enumerate(top_chunks):
        snippet = f"[Source: {c['source']}] (Chunk #{c['chunk_id']}):\n{c['content']}"
        context_snippets.append(snippet)
        sources.append({
            "source": c["source"],
            "chunk_id": c["chunk_id"],
            "score": round(c["score"], 4),
            "preview": c["content"][:160] + "..." if len(c["content"]) > 160 else c["content"]
        })

    logger.info("RAG Agent retrieved %d relevant chunks.", len(context_snippets))

    return {
        **state,
        "rag_context": context_snippets,
        "rag_sources": sources
    }

