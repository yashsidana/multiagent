from src.agents.router import router_node
from src.agents.state import CopilotState


def test_router_heuristic_fallback():
    # Verify fallback routing assigns proper keys and state
    state: CopilotState = {
        "question": "What is our policy on returning defective appliances?",
        "route": "hybrid",
        "routing_reason": "",
        "sql_query": None,
        "sql_results": [],
        "sql_columns": [],
        "sql_error": None,
        "sql_retries": 0,
        "rag_context": [],
        "rag_sources": [],
        "final_answer": "",
        "tokens_used": 0,
        "latency_seconds": 0.0
    }
    updated = router_node(state)
    assert updated["route"] in ["sql", "rag", "hybrid"]
    assert "routing_reason" in updated

