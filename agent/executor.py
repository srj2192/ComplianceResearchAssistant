"""
Executor: runs a single task by calling the appropriate tool,
then uses the LLM to synthesize a finding from the tool results.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from prompts.system import SYSTEM_PROMPT, EXECUTOR_PROMPT
from tools import rag_search, web_search

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def run_task(task: dict, goal: str) -> dict:
    """
    Executes a single task:
    1. Routes to the correct tool (rag or web)
    2. Calls the tool with the task query
    3. Uses LLM to synthesize a concise finding

    Returns the task dict updated with:
        - "raw_results": raw tool output
        - "finding": LLM-synthesized summary
        - "status": "done" or "failed"
    """
    tool = task.get("tool", "rag")
    query = task.get("query", task["title"])

    # --- Step 1: Call the tool ---
    try:
        if tool == "rag":
            raw = rag_search.search(query)
            tool_results_text = rag_search.format_results(raw)
            sources = [r["source"] for r in raw]
        elif tool == "web":
            raw = web_search.search(query)
            tool_results_text = web_search.format_results(raw)
            sources = [r["url"] for r in raw]
        else:
            raise ValueError(f"Unknown tool: {tool}")
    except Exception as e:
        task["status"] = "failed"
        task["finding"] = f"Tool execution failed: {str(e)}"
        task["raw_results"] = []
        return task

    # --- Step 2: Synthesize finding with LLM ---
    client = _get_client()

    prompt = EXECUTOR_PROMPT.format(
        goal=goal,
        task_title=task["title"],
        task_description=task["description"],
        tool_results=tool_results_text,
    )

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=512,
        messages=[
            ChatCompletionSystemMessageParam(content=SYSTEM_PROMPT, role="system"),
            ChatCompletionUserMessageParam(content=prompt, role="user"),
        ],
    )

    task["finding"] = response.choices[0].message.content.strip()
    task["raw_results"] = raw
    task["sources"] = sources
    task["status"] = "done"

    return task
