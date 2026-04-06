"""
Streamlit UI for the Compliance Research Agent.
Run with: streamlit run app.py
"""

import streamlit as st
from agent import run

# config
st.set_page_config(
    page_title="Compliance Research Agent",
    page_icon="🛡️",
    layout="wide",
)

# styles
st.markdown("""
<style>
.task-box {
    padding: 0.6rem 1rem;
    border-radius: 6px;
    margin-bottom: 0.4rem;
    font-size: 0.9rem;
}
.task-pending  { background: #f0f2f6; color: #555; }
.task-running  { background: #fff3cd; color: #856404; }
.task-done     { background: #d1e7dd; color: #0f5132; }
.task-failed   { background: #f8d7da; color: #842029; }
</style>
""", unsafe_allow_html=True)

# header
st.title("Compliance Research Agent")
st.caption("Powered by GDPR & ISO 27001 knowledge base + live regulatory search")

# sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    This agent helps you understand compliance requirements by:
    1. Breaking your goal into research tasks
    2. Searching GDPR & ISO 27001 documents (RAG)
    3. Fetching latest regulatory guidance (web)
    4. Generating a prioritized checklist

    **Documents indexed:**
    - GDPR (EU 2016/679) — `CELEX_32016R0679_EN_TXT.pdf`
    - NIST SP 800-53r5 — `NIST.SP.800-53r5.pdf`

    **Tools used:**
    - FAISS vector search (local docs)
    - Tavily web search (live updates)
    """)

# right main panel
goal = st.text_area(
    "Describe your compliance goal",
    value=st.session_state.get("goal_input", ""),
    placeholder="e.g. We're launching a fintech app in the EU and need to understand GDPR and ISO 27001 requirements...",
    height=100,
    key="goal_input",
)

run_button = st.button("Run Compliance Research", type="primary", disabled=not goal.strip())

# agent execution
if run_button and goal.strip():
    st.divider()

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Agent Progress")
        plan_placeholder = st.empty()
        task_placeholders = {}

    with col_right:
        st.subheader("Live Findings")
        findings_container = st.container()

    result_placeholder = st.empty()

    tasks_state = {}

    def render_tasks():
        with plan_placeholder.container():
            for tid, t in tasks_state.items():
                status = t.get("status", "pending")
                icon = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "failed": "❌"}.get(status, "⏳")
                css = {"pending": "task-pending", "in_progress": "task-running", "done": "task-done", "failed": "task-failed"}.get(status, "task-pending")
                tool_badge = "🔍 RAG" if t.get("tool") == "rag" else "🌐 Web"
                st.markdown(
                    f'<div class="task-box {css}">{icon} <b>{t["title"]}</b><br>'
                    f'<small>{tool_badge}</small></div>',
                    unsafe_allow_html=True,
                )

    for event in run(goal):
        etype = event["type"]
        data = event["data"]

        if etype == "plan":
            for task in data["tasks"]:
                tasks_state[task["id"]] = task
            render_tasks()

        elif etype == "task_start":
            tasks_state[data["id"]]["status"] = "in_progress"
            render_tasks()

        elif etype == "task_done":
            tasks_state[data["id"]] = data
            render_tasks()
            with findings_container:
                with st.expander(f"{data['title']}", expanded=False):
                    st.markdown(data.get("finding", ""))
                    if data.get("sources"):
                        st.caption("Sources: " + ", ".join(str(s) for s in data["sources"][:3]))

        elif etype == "task_fail":
            tasks_state[data["id"]] = data
            render_tasks()
            with findings_container:
                st.error(f"{data['title']}: {data.get('finding', 'Failed')}")

        elif etype == "result":
            st.divider()
            st.subheader("Compliance Checklist")
            st.markdown(data)

            st.download_button(
                label="Download Checklist (.md)",
                data=f"# Compliance Checklist\n\n**Goal:** {goal}\n\n{data}",
                file_name="compliance_checklist.md",
                mime="text/markdown",
            )

        elif etype == "error":
            st.error(f"Agent error: {data}")
