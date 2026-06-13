"""
judge_llm.py — local LLM-as-judge for open-ended tasks (Writing suite, Phase 3).

Writing can't be scored by exact-match, so a model grades it on a rubric. Per the
project rule there is NO API — the judge is the SAME local model. That makes the
judge weaker than the work in some cases, so we mitigate:
  - structured rubric (each criterion 1-5) instead of a vibe score
  - low temperature for stable grading
  - average across criteria, normalized to 0..1
This is noisier than code tests; treat writing scores as directional, not exact.
"""
from __future__ import annotations

import json
import re

from forge.backend import Backend, GenConfig, Message

JUDGE_SYS = """You are a strict, fair writing evaluator. Score the response to the task on
each criterion from 1 (poor) to 5 (excellent). Reply with ONE JSON object only:
{"scores": {"<criterion>": <1-5>, ...}, "note": "<one short reason>"}
Judge only what is asked. Do not reward length or filler."""


def rubric_score(task_prompt: str, answer: str, criteria: list[str],
                 backend: Backend) -> tuple[float, str]:
    crit = ", ".join(criteria)
    user = (f"TASK:\n{task_prompt}\n\nRESPONSE:\n{answer}\n\n"
            f"Score these criteria (1-5 each): {crit}")
    raw = backend.chat([Message("system", JUDGE_SYS), Message("user", user)],
                       GenConfig(temperature=0.0, json_mode=True, max_tokens=400))
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return 0.0, "judge: unparseable"
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return 0.0, "judge: unparseable"
    scores = obj.get("scores", {})
    vals = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    if not vals:
        return 0.0, "judge: no scores"
    norm = (sum(vals) / len(vals) - 1) / 4  # map 1..5 -> 0..1
    note = obj.get("note", "")[:60] + f" [{'/'.join(f'{int(v)}' for v in vals)}]"
    return round(max(0.0, min(1.0, norm)), 3), note
