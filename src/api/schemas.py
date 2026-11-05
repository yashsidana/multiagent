from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    question: str = Field(..., description="The natural language business inquiry to answer.")


class SourceItem(BaseModel):
    source: str = Field(..., description="Document file name.")
    chunk_id: Any = Field(..., description="Unique chunk identifier.")
    score: float = Field(..., description="Cosine similarity score.")
    preview: str = Field(..., description="Short preview snippet of chunk content.")


class CopilotResponse(BaseModel):
    question: str
    route: str = Field(..., description="Route selected by Router Agent: 'sql', 'rag', or 'hybrid'.")
    routing_reason: str
    final_answer: str = Field(..., description="Grounded business insight answer.")
    sql_query: Optional[str] = Field(None, description="Executed MySQL query (if quantitative).")
    sql_results: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Raw rows returned by MySQL.")
    sql_error: Optional[str] = None
    sources: List[SourceItem] = Field(default_factory=list, description="Document sources cited.")
    tokens_used: int = Field(0, description="Estimated total tokens used.")
    latency_seconds: float = Field(0.0, description="Total execution time in seconds.")


class HealthResponse(BaseModel):
    status: str
    mysql_connected: bool
    mysql_error: Optional[str] = None
    faiss_indexed: bool
    total_vectors: int


class IngestResponse(BaseModel):
    status: str
    chunks_indexed: int
    message: str

