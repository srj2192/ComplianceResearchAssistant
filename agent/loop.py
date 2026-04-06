"""
Core agent loop: orchestrates planner → executor → synthesizer.
This is the main execution engine — no frameworks, just a simple loop.
"""

from typing import Generator
from agent.planner import generate_plan
from agent.executor import run_task
from agent.synthesizer import generate_checklist


def run(goal: str) -> Generator[dict, None, None]:
    """
    Runs the full compliance agent pipeline for a given goal.

    Yields status events so the UI can show real-time progress:
        {"type": "plan",     "data": plan}
        {"type": "task_start", "data": task}
        {"type": "task_done",  "data": task}
        {"type": "task_fail",  "data": task}
        {"type": "result",   "data": checklist_text}
        {"type": "error",    "data": error_message}
    """

    try:
        plan = generate_plan(goal)
        yield {"type": "plan", "data": plan}
    except Exception as e:
        yield {"type": "error", "data": f"Planning failed: {str(e)}"}
        return

    tasks = plan["tasks"]

    for task in tasks:
        task["status"] = "in_progress"
        yield {"type": "task_start", "data": task}

        try:
            updated_task = run_task(task, goal)
            tasks[tasks.index(task)] = updated_task

            if updated_task["status"] == "done":
                yield {"type": "task_done", "data": updated_task}
            else:
                yield {"type": "task_fail", "data": updated_task}

        except Exception as e:
            task["status"] = "failed"
            task["finding"] = str(e)
            yield {"type": "task_fail", "data": task}

    try:
        checklist = generate_checklist(goal, tasks)
        yield {"type": "result", "data": checklist}
    except Exception as e:
        yield {"type": "error", "data": f"Synthesis failed: {str(e)}"}
