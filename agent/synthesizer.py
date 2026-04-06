"""
Synthesizer: takes all task findings and generates the final compliance checklist.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from prompts.system import SYSTEM_PROMPT, SYNTHESIZER_PROMPT

load_dotenv()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generate_checklist(goal: str, tasks: list[dict]) -> str:
    """
    Takes the completed tasks with findings and generates a final structured compliance checklist.
    """
    client = _get_client()

    # Build findings summary — only include completed tasks
    # Context strategy: pass task title + finding only (not raw chunks)
    # This keeps context lean: ~100 words per task vs thousands of raw chunk words
    findings_text = ""
    for task in tasks:
        if task.get("status") == "done":
            findings_text += f"\n\n### {task['title']}\n{task.get('finding', 'No finding available.')}"
        elif task.get("status") == "failed":
            findings_text += f"\n\n### {task['title']}\n[FAILED: {task.get('finding', 'Unknown error')}]"

    prompt = SYNTHESIZER_PROMPT.format(
        goal=goal,
        findings=findings_text.strip(),
    )

    response = client.chat.completions.create(
        model="gpt-4.1",
        max_tokens=2048,
        messages=[
            ChatCompletionSystemMessageParam(content=SYSTEM_PROMPT, role="system"),
            ChatCompletionUserMessageParam(content=prompt, role="user"),
        ],
    )

    return response.choices[0].message.content.strip()
