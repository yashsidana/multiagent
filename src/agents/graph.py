import time
import logging
from typing import Dict, Any
from src.agents.state import CopilotState
from src.agents.router import router_node
from src.agents.sql_agent import sql_agent_node
from src.agents.rag_agent import rag_agent_node
from src.agents.synthesis_agent import synthesis_node

logger = logging.getLogger(__name__)


def route_decision(state: CopilotState):
    """Conditional routing edge logic."""
    route = state.get("route", "hybrid")
    if route == "sql":
        return "sql_agent"
    elif route == "rag":
        return "rag_agent"
    else:
        return "hybrid"


def build_langgraph_workflow():
    """
    Builds and compiles the multi-agent state graph using LangGraph.
    Falls back gracefully to a direct pipeline if langgraph is not installed.
    """
    try:
        from langgraph.graph import StateGraph, END

        workflow = StateGraph(CopilotState)

        # 1. Add agent nodes
        workflow.add_node("router", router_node)
        workflow.add_node("sql_agent", sql_agent_node)
        workflow.add_node("rag_agent", rag_agent_node)
        workflow.add_node("synthesis", synthesis_node)

        # 2. Add edges
        workflow.set_entry_point("router")

        def route_condition(state: CopilotState):
            r = state.get("route", "hybrid")
            if r == "sql":
                return "sql_agent"
            elif r == "rag":
                return "rag_agent"
            else:
                return ["sql_agent", "rag_agent"]

        workflow.add_conditional_edges(
            "router",
            route_condition,
            {
                "sql_agent": "sql_agent",
                "rag_agent": "rag_agent",
                ["sql_agent", "rag_agent"]: ["sql_agent", "rag_agent"]
            }
        )

        workflow.add_edge("sql_agent", "synthesis")
        workflow.add_edge("rag_agent", "synthesis")
        workflow.add_edge("synthesis", END)

        return workflow.compile()

    except Exception as e:
        logger.warning("Could not compile native LangGraph: %s. Using sequential orchestrator.", str(e))
        return None


# Compiled LangGraph instance (or None if falling back)
_compiled_graph = build_langgraph_workflow()


def run_copilot_workflow(question: str) -> CopilotState:
    """
    Executes the multi-agent Business Insights Copilot workflow for a question.
    Handles timing, state transitions, and error management.
    """
    start_time = time.time()
    initial_state: CopilotState = {
        "question": question,
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

    state = initial_state

    # Execute workflow
    if _compiled_graph is not None:
        try:
            state = _compiled_graph.invoke(initial_state)
        except Exception as e:
            logger.error("LangGraph execution error: %s. Falling back to direct pipeline.", str(e))
            state = _direct_execution_pipeline(initial_state)
    else:
        state = _direct_execution_pipeline(initial_state)

    state["latency_seconds"] = round(time.time() - start_time, 3)
    return state


def _direct_execution_pipeline(state: CopilotState) -> CopilotState:
    """
    Direct Python execution of the multi-agent workflow nodes.
    Ensures rock-solid reliability across all environments.
    """
    # 1. Router
    state = router_node(state)
    route = state.get("route", "hybrid")

    # 2. Specialist Agents
    if route == "sql":
        state = sql_agent_node(state)
    elif route == "rag":
        state = rag_agent_node(state)
    else:  # hybrid
        # Run both specialists
        state = sql_agent_node(state)
        state = rag_agent_node(state)

    # 3. Synthesis
    state = synthesis_node(state)
    return state

