import json
import logging
from config.settings import settings
from src.agents.state import CopilotState
from src.agents.llm_client import llm_client

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are the Router Agent for the Business Insights Copilot.
Your job is to analyze the user's business inquiry and route it to the appropriate specialist:

1. 'sql': The question strictly asks about numeric metrics, transactional aggregations, customer counts, sales reps, quotas, orders, products, or financial totals that reside in the MySQL relational database.
2. 'rag': The question asks about corporate policies, strategy, Q4 executive summaries, product guidelines, warranty/return terms, or qualitative reasoning found in company documents.
3. 'hybrid': The question requires BOTH exact numbers/aggregations from the MySQL database AND qualitative explanations or policy context from the documents.

Few-shot examples:
Q: "What was the total revenue across all completed orders in Q4?"
{"route": "sql", "reason": "Requires aggregating order totals and filtering completed status from the MySQL database."}

Q: "What is the return policy for damaged edge appliances?"
{"route": "rag", "reason": "Requires looking up warranty and return policy documentation."}

Q: "How much was refunded to Sao Paulo Retailers, and what was the official reason for the return?"
{"route": "hybrid", "reason": "Requires MySQL to find the exact refunded order amount and documents to find the cause of the refund."}

Q: "Which sales rep achieved the highest sales and exceeded their quota?"
{"route": "sql", "reason": "Requires joining sales_reps with orders and summing item revenues from MySQL."}

Output format:
Return ONLY a valid JSON object with keys:
- "route": one of ["sql", "rag", "hybrid"]
- "reason": concise explanation for the choice
"""


def router_node(state: CopilotState) -> CopilotState:
    """
    LangGraph node: Classifies the incoming question into 'sql', 'rag', or 'hybrid'.
    """
    question = state.get("question", "")
    logger.info("Router evaluating question: %s", question)

    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": f"User question: {question}"}
    ]

    raw_response = llm_client.generate_chat_completion(
        messages=messages,
        model=settings.ROUTER_MODEL,
        temperature=0.0,
        json_mode=True
    )

    try:
        parsed = json.loads(raw_response)
        route = parsed.get("route", "hybrid").lower()
        if route not in ["sql", "rag", "hybrid"]:
            route = "hybrid"
        reason = parsed.get("reason", "Default routing applied.")
    except Exception as e:
        logger.warning("Router output JSON parse failed: %s. Defaulting to hybrid.", str(e))
        route = "hybrid"
        reason = "Parse fallback to hybrid."

    logger.info("Router decision: '%s' (Reason: %s)", route, reason)
    return {
        **state,
        "route": route,
        "routing_reason": reason,
        "sql_retries": 0
    }

