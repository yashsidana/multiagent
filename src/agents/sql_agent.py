import re
import logging
from typing import Dict, Any, List
from config.settings import settings
from src.agents.state import CopilotState
from src.agents.llm_client import llm_client
from src.database.mysql_client import readonly_mysql_client
from src.database.schema_inspector import schema_inspector

logger = logging.getLogger(__name__)

SQL_AGENT_SYSTEM_PROMPT = """You are an expert MySQL Data Engineer for the Business Insights Copilot.
Your job is to generate a single, accurate, read-only MySQL SELECT query that answers the user's question.

CRITICAL RULES:
1. ONLY produce a single SELECT statement. Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or CREATE.
2. Use MySQL dialect conventions: backticks `table`.`column`, YEAR(), QUARTER(), CURDATE(), and DATE_SUB().
3. Business Definitions:
   - "Revenue" or "Net Sales": SUM(oi.total_amount) on orders where o.status = 'Completed'.
   - "Gross Profit": SUM((p.unit_price - p.cost_price) * oi.quantity).
   - "Discounted Revenue": total_amount * (1 - (discount_pct / 100.0)).
4. Always JOIN tables properly:
   - customers.customer_id -> orders.customer_id
   - sales_reps.rep_id -> orders.rep_id
   - orders.order_id -> order_items.order_id
   - products.product_id -> order_items.product_id
5. Do NOT guess column names. Use ONLY columns shown in the provided MySQL schema.
6. Return ONLY the raw SQL query inside a markdown ```sql code block. Do not add commentary.

=== MYSQL SCHEMA & SAMPLE ROWS ===
{schema_summary}
"""

CORRECTION_PROMPT_TEMPLATE = """Your previous query encountered an error when executed against MySQL.

Previous Query:
{previous_query}

Database Error:
{error_message}

Please analyze the error, review the schema carefully, and output the corrected MySQL SELECT query inside a ```sql code block.
"""


def _extract_sql(text: str) -> str:
    """Extracts SQL query from LLM markdown response."""
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def sql_agent_node(state: CopilotState) -> CopilotState:
    """
    LangGraph node: Generates and executes a safe MySQL query with self-correction retry loop.
    """
    question = state.get("question", "")
    retries = state.get("sql_retries", 0)
    max_retries = 2

    schema_text = schema_inspector.get_schema_summary()
    system_prompt = SQL_AGENT_SYSTEM_PROMPT.format(schema_summary=schema_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Business Question: {question}"}
    ]

    last_query = ""
    last_error = None
    execution_result = None

    for attempt in range(max_retries + 1):
        if attempt > 0 and last_error:
            logger.info("SQL Agent attempting self-correction (Attempt %d/%d)", attempt, max_retries)
            messages.append({"role": "user", "content": CORRECTION_PROMPT_TEMPLATE.format(
                previous_query=last_query,
                error_message=last_error
            )})

        raw_completion = llm_client.generate_chat_completion(
            messages=messages,
            model=settings.SQL_MODEL,
            temperature=0.0
        )
        sql_query = _extract_sql(raw_completion)
        last_query = sql_query

        # Execute query against MySQL read-only connection
        execution_result = readonly_mysql_client.execute_query(sql_query)

        if execution_result["success"]:
            logger.info("MySQL query executed successfully: %s", sql_query)
            return {
                **state,
                "sql_query": execution_result["query"],
                "sql_results": execution_result["rows"],
                "sql_columns": execution_result["columns"],
                "sql_error": None,
                "sql_retries": attempt
            }
        else:
            last_error = execution_result["error"]
            logger.warning("MySQL execution failure on attempt %d: %s", attempt, last_error)

    # If all retries fail
    return {
        **state,
        "sql_query": last_query,
        "sql_results": [],
        "sql_columns": [],
        "sql_error": last_error,
        "sql_retries": max_retries
    }

