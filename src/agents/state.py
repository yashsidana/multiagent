from typing import TypedDict, List, Dict, Any, Optional


class CopilotState(TypedDict, total=False):
    """
    Shared state object flowing through the LangGraph multi-agent workflow.
    """
    # User Input
    question: str

    # Router Agent Outputs
    route: str  # 'sql', 'rag', or 'hybrid'
    routing_reason: str

    # SQL Agent Outputs
    sql_query: Optional[str]
    sql_results: List[Dict[str, Any]]
    sql_columns: List[str]
    sql_error: Optional[str]
    sql_retries: int

    # RAG Agent Outputs
    rag_context: List[str]
    rag_sources: List[Dict[str, Any]]

    # Final Synthesis Outputs
    final_answer: str
    tokens_used: int
    latency_seconds: float

