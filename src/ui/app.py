import os
import requests
import streamlit as st
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Business Insights Copilot",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API Configuration
API_BASE_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# App Header
st.title("💼 Business Insights Copilot")
st.caption("Multi-Agent Architecture: LangGraph Router • FAISS RAG • MySQL Text-to-SQL • FastAPI")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ System Status & Controls")
    
    # Check Backend Health
    try:
        health_resp = requests.get(f"{API_BASE_URL}/health", timeout=3)
        if health_resp.status_code == 200:
            hdata = health_resp.json()
            st.success(f"Backend: Online (v1.0.0)")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("MySQL", "Connected" if hdata["mysql_connected"] else "Offline")
            with col2:
                st.metric("FAISS Chunks", hdata["total_vectors"])
        else:
            st.warning("Backend returned non-200 status.")
    except Exception:
        st.error(f"Cannot reach Backend API at `{API_BASE_URL}`. Start FastAPI first.")

    st.divider()

    # Re-index Documents Button
    if st.button("🔄 Re-index Knowledge Docs"):
        with st.spinner("Indexing documents into FAISS..."):
            try:
                res = requests.post(f"{API_BASE_URL}/ingest", timeout=30)
                if res.status_code == 200:
                    st.success(res.json()["message"])
                else:
                    st.error("Failed to re-index documents.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    # Preset Sample Inquiries
    st.subheader("💡 Demo Prompt Presets")
    preset_questions = [
        "What was the total revenue by product category for completed orders?",
        "Which sales rep generated the highest revenue, and did they hit quota?",
        "What is our return policy for damaged edge appliance shipments?",
        "What are the discounting rules for Enterprise vs Mid-Market tiers?",
        "How much was refunded to Sao Paulo Retailers, and what was the official reason for the return?"
    ]

    for q in preset_questions:
        if st.button(q, key=f"btn_{abs(hash(q))}"):
            st.session_state["preset_to_send"] = q

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hello! I am your **Business Insights Copilot**. You can ask me questions requiring financial metrics from **MySQL**, corporate policies and reports from our **document base**, or a combination of both.",
            "route": None,
            "sql_query": None,
            "sql_results": None,
            "sources": [],
            "latency": None,
            "tokens": None
        }
    ]

# Display Existing Chat Messages
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display Metadata Details if assistant message
        if msg["role"] == "assistant" and msg.get("route"):
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.badge(f"Route: {msg['route'].upper()}")
            with c2:
                st.caption(f"⏱️ Latency: **{msg.get('latency', 0.0)}s**")
            with c3:
                st.caption(f"📊 Approx. Tokens: **{msg.get('tokens', 0)}**")

            # SQL Accordion
            if msg.get("sql_query"):
                with st.expander("🔍 Inspected MySQL Query & Execution"):
                    st.code(msg["sql_query"], language="sql")
                    if msg.get("sql_results"):
                        st.write("Query Result Rows:")
                        st.dataframe(pd.DataFrame(msg["sql_results"]), use_container_width=True)

            # Sources Accordion
            if msg.get("sources"):
                with st.expander(f"📄 Retrieved Document Sources ({len(msg['sources'])})"):
                    for src in msg["sources"]:
                        st.markdown(f"**{src['source']}** *(Score: {src['score']})*")
                        st.caption(src["preview"])

# Handle Input (User typing or Preset Button)
user_prompt = st.chat_input("Ask a business question (e.g., 'What was our Q4 revenue and why did hardware margins drop?')...")
if "preset_to_send" in st.session_state:
    user_prompt = st.session_state.pop("preset_to_send")

if user_prompt:
    # 1. Append user message to state
    st.session_state["messages"].append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Call backend API
    with st.chat_message("assistant"):
        with st.spinner("Analyzing inquiry across LangGraph agents..."):
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/ask",
                    json={"question": user_prompt},
                    timeout=60
                )
                if resp.status_code == 200:
                    data = resp.json()
                    final_ans = data["final_answer"]
                    route = data["route"]
                    sql_q = data.get("sql_query")
                    sql_rows = data.get("sql_results", [])
                    sources = data.get("sources", [])
                    latency = data.get("latency_seconds", 0.0)
                    tokens = data.get("tokens_used", 0)

                    st.markdown(final_ans)

                    # Show badges & expanders
                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.badge(f"Route: {route.upper()}")
                    with c2:
                        st.caption(f"⏱️ Latency: **{latency}s**")
                    with c3:
                        st.caption(f"📊 Approx. Tokens: **{tokens}**")

                    if sql_q:
                        with st.expander("🔍 Inspected MySQL Query & Execution"):
                            st.code(sql_q, language="sql")
                            if sql_rows:
                                st.write("Query Result Rows:")
                                st.dataframe(pd.DataFrame(sql_rows), use_container_width=True)

                    if sources:
                        with st.expander(f"📄 Retrieved Document Sources ({len(sources)})"):
                            for src in sources:
                                st.markdown(f"**{src['source']}** *(Score: {src['score']})*")
                                st.caption(src["preview"])

                    # Save to state
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": final_ans,
                        "route": route,
                        "sql_query": sql_q,
                        "sql_results": sql_rows,
                        "sources": sources,
                        "latency": latency,
                        "tokens": tokens
                    })
                else:
                    err_msg = f"API error {resp.status_code}: {resp.text}"
                    st.error(err_msg)
            except Exception as e:
                st.error(f"Failed to communicate with API: {str(e)}")

