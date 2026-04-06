"""
Planner: takes a user goal and returns a structured task list (JSON).
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from prompts.system import SYSTEM_PROMPT, PLANNER_PROMPT

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generate_plan(goal: str) -> dict:
    """
    Takes a high-level compliance goal and returns a structured task plan.

    Returns:
        {
            "tasks": [
                {"id": "t1", "title": "...", "description": "...", "tool": "rag"|"web", "query": "..."},
                ...
            ]
        }
    """
    client = _get_client()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=1024,
        messages=[
            ChatCompletionSystemMessageParam(content=SYSTEM_PROMPT, role="system"),
            ChatCompletionUserMessageParam(content=PLANNER_PROMPT.format(goal=goal), role="user"),
        ],
    )

    raw = response.choices[0].message.content.strip()


    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Planner returned invalid JSON: {e}\nRaw output:\n{raw}")

    if "tasks" not in plan or not isinstance(plan["tasks"], list):
        raise ValueError(f"Planner returned unexpected structure: {plan}")

    for task in plan["tasks"]:
        task["status"] = "pending"

    return plan
