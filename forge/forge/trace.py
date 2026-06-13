"""
trace.py — save/replay agent runs (Phase 20, observability).

"You can't improve what you can't see." Every solve can dump its full step-by-step
trace (thought / tool / args / observation) to bench/results/traces/, so you can
replay a run, see where the agent went wrong, and mine failures for the improvement
loop. Lightweight JSON; no extra deps.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

TRACE_DIR = Path(__file__).resolve().parent.parent / "bench" / "results" / "traces"


def save(task: str, result, label: str = "solve") -> Path:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{int(time.time())}_{label}.json"
    path = TRACE_DIR / fname
    data = {
        "ts": time.time(),
        "task": task,
        "answer": result.answer,
        "stopped_reason": getattr(result, "stopped_reason", ""),
        "steps": [
            {"thought": s.thought, "action": s.action, "args": s.args,
             "observation": (s.observation or "")[:1000]}
            for s in result.steps
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def latest() -> dict | None:
    if not TRACE_DIR.exists():
        return None
    files = sorted(TRACE_DIR.glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def render(data: dict) -> str:
    if not data:
        return "No traces yet. Run `python cli.py solve \"...\"` first."
    lines = [f"TASK: {data['task'][:120]}",
             f"STOP: {data['stopped_reason']}  ({len(data['steps'])} steps)", ""]
    for i, s in enumerate(data["steps"], 1):
        lines.append(f"[{i}] {s['action']}  args={json.dumps(s['args'])[:80]}")
        if s["thought"]:
            lines.append(f"     thought: {s['thought'][:100]}")
        if s["observation"]:
            lines.append(f"     obs: {s['observation'][:120].strip()}")
    lines += ["", f"ANSWER: {data['answer'][:300]}"]
    return "\n".join(lines)
