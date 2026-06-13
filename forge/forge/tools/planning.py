"""
planning.py — explicit task planning, ported from Claude Code's TodoWrite pattern.

Why it matters: externalizing a plan (instead of holding it implicitly in the
generation) keeps a small model on-track across many steps — it can re-read what's
left and what's done. The plan lives in the agent's run state and is echoed back so
the model sees its own checklist each turn.
"""
from __future__ import annotations

from . import tool

# Per-run plan store (reset by the agent at the start of each run).
_PLAN: list[dict] = []


def reset_plan() -> None:
    _PLAN.clear()


def render_plan() -> str:
    if not _PLAN:
        return ""
    marks = {"todo": "[ ]", "doing": "[~]", "done": "[x]"}
    return "\n".join(f"{marks.get(s['status'], '[ ]')} {s['step']}" for s in _PLAN)


@tool(
    description=(
        "Create or update your task plan for a multi-step task. Pass the full list of "
        "steps each time with their status. Use this to plan before acting and to mark "
        "progress. Statuses: 'todo', 'doing', 'done'. Keep exactly one 'doing'."
    ),
    parameters={
        "steps": {"type": "array", "description": "list of {step: str, status: 'todo'|'doing'|'done'}"},
    },
)
def update_plan(steps: list) -> str:
    _PLAN.clear()
    for s in steps:
        if isinstance(s, dict) and "step" in s:
            _PLAN.append({"step": str(s["step"]), "status": s.get("status", "todo")})
        elif isinstance(s, str):
            _PLAN.append({"step": s, "status": "todo"})
    return "Plan updated:\n" + render_plan()
