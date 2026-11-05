import asyncio
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from src.api.schemas import (
    QuestionRequest,
    CopilotResponse,
    HealthResponse,
    IngestResponse,
    SourceItem
)
from src.agents.graph import run_copilot_workflow
from src.database.mysql_client import readonly_mysql_client
from src.database.schema_inspector import schema_inspector
from src.rag.vector_store import vector_store
from src.rag.ingest import ingest_documents

logger = logging.getLogger(__name__)
api_router = APIRouter()


@api_router.get("/health", response_model=HealthResponse)
def health_check():
    """Checks MySQL connectivity and FAISS index state."""
    db_ok, db_err = readonly_mysql_client.test_connection()
    faiss_ok = vector_store.index is not None and vector_store.index.ntotal > 0
    total_vecs = vector_store.index.ntotal if vector_store.index else 0

    return HealthResponse(
        status="healthy" if (db_ok or faiss_ok) else "degraded",
        mysql_connected=db_ok,
        mysql_error=db_err,
        faiss_indexed=faiss_ok,
        total_vectors=total_vecs
    )


@api_router.post("/ask", response_model=CopilotResponse)
def ask_question(request: QuestionRequest):
    """
    Executes the multi-agent pipeline: Router -> (SQL Agent and/or RAG Agent) -> Synthesis.
    Returns complete grounded answer, sources, executed SQL, and performance metrics.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        state = run_copilot_workflow(request.question)

        sources = [
            SourceItem(
                source=s["source"],
                chunk_id=s["chunk_id"],
                score=s["score"],
                preview=s["preview"]
            )
            for s in state.get("rag_sources", [])
        ]

        return CopilotResponse(
            question=state.get("question", request.question),
            route=state.get("route", "hybrid"),
            routing_reason=state.get("routing_reason", ""),
            final_answer=state.get("final_answer", ""),
            sql_query=state.get("sql_query"),
            sql_results=state.get("sql_results", []),
            sql_error=state.get("sql_error"),
            sources=sources,
            tokens_used=state.get("tokens_used", 0),
            latency_seconds=state.get("latency_seconds", 0.0)
        )
    except Exception as e:
        logger.error("Error processing query: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal copilot error: {str(e)}")


@api_router.post("/ask/stream")
async def ask_question_stream(request: QuestionRequest):
    """
    Simulates SSE token streaming for the synthesized response to optimize perceived latency.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    async def event_generator():
        # Run workflow in background thread
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, run_copilot_workflow, request.question)

        # Send metadata first
        meta_event = {
            "type": "metadata",
            "route": state.get("route"),
            "routing_reason": state.get("routing_reason"),
            "sql_query": state.get("sql_query"),
            "sources": state.get("rag_sources", [])
        }
        yield f"data: {json.dumps(meta_event)}\n\n"

        # Stream chunks of final answer
        text = state.get("final_answer", "")
        chunk_size = 8
        for i in range(0, len(text), chunk_size):
            yield f"data: {json.dumps({'type': 'token', 'content': text[i:i+chunk_size]})}\n\n"
            await asyncio.sleep(0.015)

        # Send completion event
        yield f"data: {json.dumps({'type': 'done', 'latency': state.get('latency_seconds')})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@api_router.post("/ingest", response_model=IngestResponse)
def trigger_ingestion():
    """Triggers offline document re-indexing into FAISS."""
    try:
        count = ingest_documents()
        return IngestResponse(
            status="success",
            chunks_indexed=count,
            message=f"Indexed {count} chunks into FAISS."
        )
    except Exception as e:
        logger.error("Ingestion failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@api_router.get("/schema")
def get_mysql_schema():
    """Returns the inspected MySQL database schema and sample data."""
    summary = schema_inspector.get_schema_summary()
    return {"schema": summary}

