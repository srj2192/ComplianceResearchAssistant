# Compliance Research Agent

A small AI agent that helps compliance teams understand what GDPR and NIST SP 800-53 requirements apply to their situation. You describe your goal, the agent breaks it into research tasks, searches the regulatory documents, and produces a prioritized checklist with citations.

No agent frameworks used — custom loop, prompts, and context handling throughout.

---

## How the agent works

The user types a compliance goal. The agent runs three stages:

**1. Planning** — GPT-4.1-mini reads the goal and returns a JSON list of 4-6 research tasks, each tagged with which tool to use (RAG or web search).

**2. Execution** — For each task, the agent calls the right tool, gets results back, then asks the LLM to write a short finding based only on what the tool returned. This repeats until all tasks are done.

**3. Synthesis** — GPT-4.1 takes all the findings and produces the final checklist, grouped by theme, with priority levels and source citations.

The loop itself is about 30 lines in `agent/loop.py` — a simple generator that yields status events so the UI can show real-time progress.

---

## Tools

**FAISS RAG** — The two regulatory PDFs (GDPR and NIST SP 800-53r5) are chunked into 500-word segments, embedded with `all-MiniLM-L6-v2`, and stored in a local FAISS index. When a task needs to look up specific requirements, it does a semantic search over this index and gets back the top 5 most relevant chunks.

**Tavily Web Search** — For tasks that need current information (recent enforcement actions, updated guidance, etc.), the agent calls Tavily, filtered to authoritative domains like `edpb.europa.eu`, `ico.org.uk`, and `nist.gov`.

The planner decides which tool each task should use. RAG for specific article/control lookups, web for anything that might have changed recently.

---

## Context strategy

The main challenge is that GDPR alone is ~88 pages. Passing the full document into every LLM call isn't practical.

The approach here is: retrieve first, summarize second, keep only the summary. Each task gets the top 5 retrieved chunks (~800 tokens), the LLM writes a 4-6 sentence finding, and only that finding goes forward to the synthesizer. By the time we hit synthesis, the context is just the goal plus one short paragraph per task — maybe 600 tokens total instead of tens of thousands.

Raw chunks are never accumulated across tasks. Each task starts clean.

---

## How I would evaluate it

**The three things I'd check first:**

1. **Citation accuracy** — Does every checklist item cite a real article or control? Pick 10 outputs, manually verify each citation against the source document. Any fabricated reference is a hard failure. This is the most important check for a compliance tool.

2. **Retrieval relevance** — For a known query like "data retention requirements", do the top 3 FAISS results actually contain the answer? If not, the chunk size or embedding model needs tuning. Easy to spot by logging which chunks get returned.

3. **Coverage on known scenarios** — Run the 5 test scenarios below and check whether the expected key requirements appear in the output. For example, a healthcare SaaS query should always surface GDPR Article 9 (special category data) and Article 35 (DPIA). If it doesn't, something is wrong with retrieval or the planner prompt.

**Optional — if more time was available:**

- **LLM-as-judge scoring** — Send the generated checklist to GPT-4 with a rubric (accuracy, completeness, actionability, 1-5 each) and log the scores over many runs. Makes regression testing fast.
- **Hallucination rate** — Track how often the model adds requirements that aren't in the retrieved chunks. Can be caught by comparing finding text against the raw tool results.
- **Latency per task** — Log how long each tool call and LLM call takes. Useful for identifying which step is the bottleneck.

---

## Evaluation scenarios

**Scenario 1 — Healthcare SaaS**
Goal: "We're building a healthcare SaaS app in the EU that stores patient data. What do we need to comply with?"
Pass: checklist includes GDPR Art. 9 (special categories), Art. 35 (DPIA), Art. 32 (security), and relevant NIST access control and audit logging controls.

**Scenario 2 — EU to US data transfer**
Goal: "We want to move EU customer data to our US AWS servers. What are the requirements?"
Pass: agent surfaces GDPR Chapter V, Standard Contractual Clauses, and references the EU-US Data Privacy Framework.

**Scenario 3 — Small startup, DPO question**
Goal: "We're a 10-person startup processing user emails. Do we need a Data Protection Officer?"
Pass: agent correctly identifies Art. 37 thresholds and concludes a DPO is likely not required at this scale, while noting exceptions.

**Scenario 4 — Cloud SaaS security controls**
Goal: "What security controls do we need for a cloud SaaS product under NIST 800-53?"
Pass: agent returns a scoped list of controls (access control, audit, configuration management) rather than dumping all 1000+ controls.

**Scenario 5 — Out of scope**
Goal: "Help me write a Python script."
Pass: agent redirects to compliance aspects or declines gracefully. Should not hallucinate regulatory requirements.

---

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Add API keys to .env
cp .env.example .env

# Build the FAISS index
python ingestion/ingest_docs.py

# Start the app
streamlit run app.py 

Note: streamlit take few second s to load wait for it. 
```

API keys needed:
- OpenAI — platform.openai.com
- Tavily — app.tavily.com (used free tier: only upto 1000 searches/month)
---

## Project structure

```
├── agent/
│   ├── loop.py          # the main agent loop
│   ├── planner.py       # goal → task list
│   ├── executor.py      # task → tool → finding
│   └── synthesizer.py   # findings → checklist
├── tools/
│   ├── rag_search.py    # FAISS search
│   └── web_search.py    # Tavily search
├── ingestion/
│   └── ingest_docs.py   # builds the FAISS index from PDFs
├── prompts/
│   └── system.py        # all prompts in one place
├── docs/                # put your PDFs here
├── app.py               # Streamlit UI
└── requirements.txt
```

---

## Trade-offs and what I'd do differently

The planner assigns each task a tool upfront rather than letting the LLM decide dynamically, but dynamic tool selection tends to make unexpected choices that are hard to debug.

FAISS with IndexFlatL2 does exact nearest-neighbor search. For 598 chunks this is fine. At 100k+ chunks I'd switch to an approximate index (IVF) or move to a managed vector DB.

The runs are stateless — no session history is kept. This keeps things simple but means you can't ask follow-up questions. Adding multi-turn support would be the first thing I'd build next.
