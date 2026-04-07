
import os
import json
import openai
from openai import OpenAI
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionUserMessageParam

load_dotenv()

_client = None

GUARDRAIL_PROMPT = """You are a compliance assistant intake filter.

Decide if the following user input is related to compliance, regulation, data protection,
security controls, or legal/professional information topics (GDPR, NIST, ISO, tax, finance,
healthcare regulations, etc.).

Respond ONLY with valid JSON in this exact format:
{{"is_relevant": true, "reason": "one sentence"}}
or
{{"is_relevant": false, "reason": "one sentence"}}

User input: {goal}"""


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def check(goal: str) -> dict:
    """
    Returns {"is_relevant": bool, "reason": str}
    Runs before the agent pipeline — fast, cheap, 100 tokens max.
    Fails open: if the check itself errors, we let the agent run.
    """
    if not goal or len(goal.strip()) < 10:
        return {"is_relevant": False, "reason": "Please describe your compliance goal in more detail."}

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=100,
            temperature=0,
            messages=[
                ChatCompletionUserMessageParam(
                    role="user",
                    content=GUARDRAIL_PROMPT.format(goal=goal)),
            ],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except (openai.OpenAIError, json.JSONDecodeError, KeyError, IndexError, AttributeError):
        return {"is_relevant": True, "reason": "Guardrail check skipped."}
