# Compliance Research Agent

An AI agent built on the pattern of a plan and execute agent that takes a compliance goal, breaks it into research tasks, executes them against GDPR and NIST SP 800-53 documents, and produces a prioritized checklist with citations.

---

## How the agent loop works

The user describes a compliance goal. The agent runs three stages in sequence:

**Plan** — GPT-4.1-mini reads the goal and returns a structured JSON list of 4-6 tasks. Each task has a title, description, and a tool hint (RAG or web search). This is the TODO list.

**Execute** — The loop iterates through each task. For every task it calls the assigned tool, gets results back, and asks the LLM to write a short finding based only on what the tool returned. The task status updates from pending → in progress → done. Each task is independent — nothing from a previous task leaks into the next one.

**Synthesize** — Once all tasks are done, GPT-4.1 takes the goal and all the findings and produces the final compliance checklist with priority levels and source citations.

The loop lives in `agent/loop.py` and is a plain Python generator that yields status events. The Streamlit UI consumes these events to show live task progress.

---

## Tools integrated

**FAISS vector search (RAG)** — GDPR and NIST SP 800-53r5 PDFs are chunked into 500-word segments, embedded with `sentence-transformers`, and stored in a local FAISS index. When a task needs specific article or control lookups, it searches this index and retrieves the top 5 most relevant chunks.

**Tavily web search** — For tasks that need current information (recent enforcement, updated guidance), the agent calls Tavily filtered to authoritative domains like `edpb.europa.eu`, `ico.org.uk`, and `nist.gov`.

---

## Context strategy

GDPR is ~88 pages. NIST 800-53 is ~500 pages. Passing full documents into every call isn't feasible.

The approach: retrieve → summarize → discard. Each task gets the top 5 chunks from the tool (~800 tokens). The LLM writes a 4-6 sentence finding from those chunks. The raw chunks are then dropped — they never accumulate. Only the short finding moves forward.

By synthesis, the context is the original goal plus one short paragraph per task — roughly 600 tokens total. Every LLM call starts clean with no history from previous tasks.

Within a single run, the agent maintains state: the task list with statuses and the findings dict are passed through the loop and available to the synthesizer. There is no cross-run memory — each new goal starts fresh.

---

## Setup

```bash
uv sync
cp .env.example .env        # add OpenAI and Tavily API keys
python ingestion/ingest_docs.py   # build FAISS index once
streamlit run app.py
```

---

## Project structure

```
├── agent/
│   ├── loop.py          # main agent loop
│   ├── planner.py       # goal → task list
│   ├── executor.py      # task → tool → finding
│   ├── synthesizer.py   # findings → checklist
│   └── guardrails.py    # input validation
├── tools/
│   ├── rag_search.py    # FAISS semantic search
│   └── web_search.py    # Tavily web search
├── ingestion/
│   └── ingest_docs.py   # PDF → FAISS index
├── prompts/
│   └── system.py        # all prompts
├── docs/                # regulatory PDFs
└── app.py               # Streamlit UI
```
