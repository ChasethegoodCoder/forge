"""
harness.py — runs the benchmark suite through the agent, scores every task, and
appends a timestamped record to bench/results/history.jsonl. That history file IS
the project's progress ledger: every roadmap change must show up as a number that
moves here, or it didn't help.

Usage:
    python -m bench.harness                 # run all suites with default model
    python -m bench.harness --suite coding  # just one suite
    python -m bench.harness --model qwen2.5:14b-instruct-q4_K_M
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend  # noqa: E402
from bench.judge import score_one      # noqa: E402

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def load_suite(name: str) -> list[dict]:
    f = TASKS_DIR / f"{name}.jsonl"
    return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(suites: list[str], model: str | None, max_steps: int, critic: bool = False) -> dict:
    backend = get_backend(model)
    if critic:
        from forge.orchestrator import Orchestrator
        agent = Orchestrator(backend, max_steps=max_steps)
        agent.backend = backend  # rubric judge needs a backend handle
    else:
        agent = Agent(backend, max_steps=max_steps)
    started = time.time()
    per_task, per_cat = [], {}

    for suite in suites:
        for task in load_suite(suite):
            t0 = time.time()
            res = agent.run(task["prompt"])
            spec = task["score"]
            if spec.get("type") == "rubric":
                from bench.judge_llm import rubric_score
                sc, note = rubric_score(task["prompt"], res.answer,
                                        spec["criteria"], agent.backend)
            else:
                # code the agent executed during the run — fallback source for scoring
                executed = [s.args.get("code", "") for s in res.steps
                            if s.action == "run_python" and isinstance(s.args, dict)]
                sc, note = score_one(res.answer, spec, extra_code=executed)
            dt = round(time.time() - t0, 1)
            row = {
                "id": task["id"], "suite": suite,
                "category": task.get("category", suite),
                "difficulty": task.get("difficulty", 0),
                "score": sc, "note": note, "secs": dt,
                "steps": len(res.steps), "stop": res.stopped_reason,
            }
            per_task.append(row)
            per_cat.setdefault(row["category"], []).append(sc)
            mark = "PASS" if sc >= 1 else "FAIL" if sc <= 0 else "PART"
            print(f"  [{mark}] {task['id']:<8} {sc:.2f}  {dt:>4}s  {note[:50]}")

    overall = sum(r["score"] for r in per_task) / max(len(per_task), 1)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": backend.name,
        "host": platform.node(),
        "suites": suites,
        "n_tasks": len(per_task),
        "overall": round(overall, 4),
        "by_category": {k: round(sum(v) / len(v), 4) for k, v in per_cat.items()},
        "elapsed_s": round(time.time() - started, 1),
        "tasks": per_task,
    }
    (RESULTS / "history.jsonl").open("a", encoding="utf-8").write(json.dumps(record) + "\n")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", action="append", help="suite name (repeatable)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--critic", action="store_true", help="use planner/coder/critic orchestrator")
    args = ap.parse_args()
    suites = args.suite or ["reasoning", "coding", "writing", "agent"]

    print(f"\n=== Forge Benchmark — model={args.model or 'default'} suites={suites} "
          f"{'(critic)' if args.critic else ''} ===")
    rec = run(suites, args.model, args.max_steps, critic=args.critic)
    print("\n--- SUMMARY ---")
    print(f"model:    {rec['model']}")
    print(f"overall:  {rec['overall']*100:.1f}%  ({rec['n_tasks']} tasks, {rec['elapsed_s']}s)")
    for cat, v in rec["by_category"].items():
        print(f"  {cat:<12} {v*100:5.1f}%")
    print(f"\nlogged -> bench/results/history.jsonl")


if __name__ == "__main__":
    main()
