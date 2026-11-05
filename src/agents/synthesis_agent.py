import json
import logging
from typing import List, Dict, Any
from config.settings import settings
from src.agents.state import CopilotState
from src.agents.llm_client import llm_client

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are the Senior Business Insights Synthesizer for the Business Insights Copilot.
Your job is to craft a clear, professional, executive-ready answer to the user's inquiry based strictly on the retrieved data.

GROUNDING & INTEGRITY RULES:
1. Strict Numerical Grounding: ONLY report figures and counts that are present in the provided MySQL Query Results. Never invent, extrapolate, or guess numbers.
2. Strict Document Grounding: Qualitative claims and policies must be supported by the provided Document Context. Always cite the document filename in brackets, e.g. [q4_business_review.md].
3. Transparency: Mention the executed SQL query when answering quantitative questions so users can audit the logic.
4. Handling Missing Data: If query results are empty or documents do not contain the answer, state clearly and honestly that the records do not contain this information. Do not guess.
5. Formatting: Use structured Markdown headers, bullet points, and concise key metric callouts.
"""

SYNTHESIS_USER_TEMPLATE = """User Business Question: {question}

=== ROUTING DECISION ===
Route: {route} (Reason: {routing_reason})

=== MYSQL DATABASE RESULTS ===
Executed Query: {sql_query}
Query Error (if any): {sql_error}
Query Data Rows: {sql_results}

=== RETRIEVED DOCUMENT CONTEXT ===
{rag_context}

Please provide the final synthesized response according to the instructions.
"""


def synthesis_node(state: CopilotState) -> CopilotState:
    """
    LangGraph node: Fuses structured MySQL records and unstructured document excerpts
    into a grounded executive response with source citations.
    """
    question = state.get("question", "")
    route = state.get("route", "hybrid")
    routing_reason = state.get("routing_reason", "")
    sql_query = state.get("sql_query", "None")
    sql_error = state.get("sql_error", "None")
    sql_results = json.dumps(state.get("sql_results", []), indent=2, default=str)
    
    rag_context_list = state.get("rag_context", [])
    rag_context = "\n\n".join(rag_context_list) if rag_context_list else "No document chunks retrieved."

    user_content = SYNTHESIS_USER_TEMPLATE.format(
        question=question,
        route=route,
        routing_reason=routing_reason,
        sql_query=sql_query,
        sql_error=sql_error,
        sql_results=sql_results,
        rag_context=rag_context
    )

    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    logger.info("Synthesis node generating final answer...")
    final_answer = llm_client.generate_chat_completion(
        messages=messages,
        model=settings.SYNTHESIS_MODEL,
        temperature=0.1,
        max_tokens=1200
    )

    # Estimate token usage
    approx_tokens = (len(user_content) + len(final_answer)) // 4

    return {
        **state,
        "final_answer": final_answer,
        "tokens_used": approx_tokens
    }

