"""
clarify.py — ask a multiple-choice question when a request is ambiguous (like I do).

Before building something underspecified, a good agent asks "did you mean A or B?" with
concrete options and an "Other" escape, instead of guessing wrong. This produces the
STRUCTURED question the UI renders as buttons; the CLI renders it as a numbered prompt.

    q = ask(backend, "make me a game")
    -> {"question": "What kind of game?",
        "options": ["Platformer (Geometry Dash style)", "Puzzle", "Text adventure"]}
    (or None if the request is already clear)
"""
from __future__ import annotations

import json
import re

from .backend import Backend, GenConfig, Message

SYS = """Decide if the user's build request is ambiguous enough that you should ask ONE
clarifying question before starting. If it's already clear, reply {"clear": true}.
If not, reply with a single question and 2-4 concrete options:
{"question": "<short question>", "options": ["<option A>", "<option B>", ...]}
Only ask when it genuinely changes what you'd build. Reply JSON only."""


def ask(backend: Backend, task: str) -> dict | None:
    raw = backend.chat([Message("system", SYS), Message("user", task)],
                       GenConfig(temperature=0.1, json_mode=True, max_tokens=200))
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    if obj.get("clear") or not obj.get("question") or not obj.get("options"):
        return None
    opts = [str(o) for o in obj["options"]][:4]
    return {"question": str(obj["question"]), "options": opts, "allow_other": True}


def prompt_cli(q: dict) -> str:
    """CLI rendering: show numbered options + an 'Other' free-text choice. Returns the
    chosen text. (The UI renders the same q dict as clickable buttons + a text field.)"""
    print(f"\n{q['question']}")
    for i, o in enumerate(q["options"], 1):
        print(f"  {i}. {o}")
    print(f"  {len(q['options']) + 1}. Other (type your own)")
    try:
        raw = input("choose> ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    if raw.isdigit():
        n = int(raw)
        if 1 <= n <= len(q["options"]):
            return q["options"][n - 1]
        if n == len(q["options"]) + 1:
            try:
                return input("your answer> ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""
    return raw  # they typed free text directly
