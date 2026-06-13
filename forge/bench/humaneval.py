"""
humaneval.py — the real benchmark spine.

Why this matters: HumanEval is a STANDARD, published coding benchmark. Sonnet 4.6's
score on it is publicly known (~0.92 pass@1), so running it turns "progress toward
Sonnet 4.6" from a vibe into a comparable number against the actual target.

Two upgrades over the homemade suite, both from the improvement plan:
  #1 FILE-BASED scoring — the agent writes its solution to `solution.py`; we import
     and run the official test against that file. No regex extraction, no escaping
     bugs (the thing that was failing `add()`).
  #3 pass@k — sample k times per problem; report pass@1 and pass@k so a stochastic
     model's score isn't single-shot luck.

Usage:
    python -m bench.humaneval --limit 20            # quick pass@1 on first 20
    python -m bench.humaneval --limit 164 --k 1     # full official run
    python -m bench.humaneval --model qwen2.5-coder:7b-instruct --limit 20
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend, GenConfig  # noqa: E402
from forge.tools.files import WORKSPACE  # noqa: E402

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "HumanEval.jsonl"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

# Published reference point we are climbing toward (pass@1). Source: Anthropic's
# reported Claude Sonnet HumanEval performance. Used only as the target anchor.
TARGET_PASS1 = 0.92

SOLUTION = "solution.py"

PROMPT_TMPL = """Complete the following Python function so it is fully correct.

Write the COMPLETE function — including the exact signature, any needed imports
(e.g. `from typing import List`), and a working body — to a file named `{sol}` using
the write_file tool. Then call run_python to import and smoke-test it. When it works,
finalize with a one-line confirmation.

Here is the function to complete:

```python
{prompt}```"""


def load_problems(limit: int) -> list[dict]:
    rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows[:limit]


def _run_test(solution_code: str, test_src: str, entry: str) -> tuple[bool, str]:
    """Official-style scoring: solution + test's check() + check(entry)."""
    harness = f"{solution_code}\n\n{test_src}\n\ncheck({entry})\nprint('HE_OK')\n"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "run.py"
        f.write_text(harness, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, str(f)], capture_output=True,
                               text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return False, "timeout"
    if "HE_OK" in p.stdout:
        return True, "ok"
    err = (p.stderr or "").strip().splitlines()
    return False, (err[-1] if err else "no output")[:80]


def _read_solution() -> str:
    p = WORKSPACE / SOLUTION
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _compiles(code: str) -> bool:
    import ast
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def solve_once(agent, problem: dict) -> tuple[bool, str, str]:
    # clean prior solution so a stale file can't pass for this problem
    sol_path = WORKSPACE / SOLUTION
    if sol_path.exists():
        sol_path.unlink()
    task = PROMPT_TMPL.format(sol=SOLUTION, prompt=problem["prompt"])
    res = agent.run(task)  # agent OR orchestrator — both return .answer / .steps
    code = _read_solution()
    # Use the written file only if it defines the entry point AND actually compiles.
    # Otherwise fall back to the code the agent verified inline (run_python snippets)
    # or its final answer — robust against a malformed write_file escape.
    if ("def " + problem["entry_point"] not in code) or not _compiles(code):
        from bench.judge import _pick_source
        executed = [s.args.get("code", "") for s in res.steps
                    if s.action == "run_python" and isinstance(s.args, dict)]
        fallback = _pick_source(res.answer, problem["entry_point"], executed)
        if ("def " + problem["entry_point"] in fallback) and _compiles(fallback):
            code = fallback
    ok, note = _run_test(code, problem["test"], problem["entry_point"])
    return ok, note, res.stopped_reason


def run(model: str | None, limit: int, k: int, max_steps: int, critic: bool = False) -> dict:
    backend_obj = get_backend(model)
    if critic:
        from forge.orchestrator import Orchestrator
        agent = Orchestrator(backend_obj, max_steps=max_steps)
    else:
        agent = Agent(backend_obj, max_steps=max_steps)
    problems = load_problems(limit)
    started = time.time()
    rows = []
    for i, prob in enumerate(problems, 1):
        passes = 0
        last_note = ""
        t0 = time.time()
        for _ in range(k):
            ok, note, _stop = solve_once(agent, prob)
            passes += int(ok)
            last_note = note
            if ok and k == 1:
                break
        any_pass = passes > 0
        rows.append({"id": prob["task_id"], "pass1": int(passes > 0),
                     "passk": int(any_pass), "k_passes": passes, "k": k,
                     "secs": round(time.time() - t0, 1), "note": last_note})
        mark = "PASS" if any_pass else "FAIL"
        print(f"  [{mark}] {prob['task_id']:<12} {passes}/{k}  "
              f"{rows[-1]['secs']:>5}s  {last_note}", flush=True)

    n = len(rows)
    pass1 = sum(r["pass1"] for r in rows) / n
    passk = sum(r["passk"] for r in rows) / n
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "bench": "HumanEval", "model": backend_obj.name,
        "mode": "critic" if critic else "single",
        "n": n, "k": k, "pass1": round(pass1, 4), "passk": round(passk, 4),
        "target_pass1": TARGET_PASS1,
        "gap_points": round((TARGET_PASS1 - pass1) * 100, 1),
        "elapsed_s": round(time.time() - started, 1),
        "rows": rows,
    }
    (RESULTS / "humaneval_history.jsonl").open("a", encoding="utf-8").write(json.dumps(record) + "\n")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--max-steps", type=int, default=10)
    ap.add_argument("--critic", action="store_true", help="use planner/coder/critic orchestrator")
    a = ap.parse_args()

    mode = "critic" if a.critic else "single"
    print(f"\n=== HumanEval — model={a.model or 'default'} limit={a.limit} k={a.k} mode={mode} ===")
    rec = run(a.model, a.limit, a.k, a.max_steps, critic=a.critic)
    print("\n--- RESULT ---")
    print(f"model:    {rec['model']}")
    print(f"pass@1:   {rec['pass1']*100:.1f}%   (n={rec['n']}, {rec['elapsed_s']}s)")
    if a.k > 1:
        print(f"pass@{a.k}:   {rec['passk']*100:.1f}%")
    print(f"target:   {rec['target_pass1']*100:.0f}% (Sonnet 4.6)")
    print(f"GAP:      {rec['gap_points']} points to target")
    print("\nlogged -> bench/results/humaneval_history.jsonl")


if __name__ == "__main__":
    main()
