"""
mbpp.py — MBPP benchmark (Mostly Basic Python Problems). A second STANDARD coding
benchmark alongside HumanEval, so a single noisy number doesn't fool us. Different
problems, natural-language prompts, 3 hidden asserts each.

Same honesty caveats as HumanEval: it's older/public, so partly in training data.
Use it as ANOTHER data point, not gospel. The contamination-resistant truth lives in
LiveCodeBench / SWE-bench (see docs/HARDER_BENCHMARKS.md).

    python -m bench.mbpp --limit 40 --mode raw
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend, GenConfig, Message  # noqa: E402
from bench.judge import clean_source, _extract_code  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "mbpp.json"
RESULTS = Path(__file__).resolve().parent / "results"

RAW_SYS = ("You are an expert Python programmer. Write ONLY the complete function "
           "(imports + def + body) inside one ```python block. No prose, no tests.")


def load(limit: int) -> list[dict]:
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    return rows[:limit]


def _entry(code: str) -> str:
    m = re.search(r"def\s+(\w+)\s*\(", code)
    return m.group(1) if m else ""


def _score(sol: str, prob: dict) -> tuple[bool, str]:
    harness = (sol + "\n" + "\n".join(prob.get("test_imports", [])) + "\n"
               + "\n".join(prob["test_list"]) + "\nprint('MBPP_OK')\n")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.py"
        f.write_text(harness, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, "-B", str(f)], capture_output=True,
                               text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return False, "timeout"
    if "MBPP_OK" in p.stdout:
        return True, "ok"
    err = (p.stderr or "").strip().splitlines()
    return False, (err[-1] if err else "fail")[:70]


def _prompt(prob: dict) -> str:
    return (f"Write a Python function for this task:\n{prob['prompt']}\n\n"
            f"It must pass:\n" + "\n".join(prob["test_list"]))


def run(model, limit, mode, max_steps):
    backend = get_backend(model)
    agent = Agent(backend, max_steps=max_steps) if mode == "agent" else None
    rows, t0 = [], time.time()
    for i, prob in enumerate(load(limit), 1):
        entry = _entry(prob["code"])
        ts = time.time()
        if mode == "raw":
            out = backend.chat([Message("system", RAW_SYS), Message("user", _prompt(prob))],
                               GenConfig(temperature=0.1))
            sol = clean_source([_extract_code(out)], entry) or _extract_code(out)
        else:
            res = agent.run(_prompt(prob) + "\n\nWrite the function in your final answer.")
            executed = [s.args.get("code", "") for s in res.steps
                        if s.action == "run_python" and isinstance(s.args, dict)]
            sol = clean_source([_extract_code(res.answer)] + executed, entry) or _extract_code(res.answer)
        ok, note = _score(sol, prob)
        rows.append({"id": prob["task_id"], "pass": int(ok), "secs": round(time.time()-ts,1)})
        print(f"  [{'PASS' if ok else 'FAIL'}] mbpp/{prob['task_id']:<4} {rows[-1]['secs']:>5}s  {note}", flush=True)

    score = sum(r["pass"] for r in rows) / len(rows)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "bench": "MBPP",
           "model": backend.name, "mode": mode, "n": len(rows),
           "pass1": round(score, 4), "elapsed_s": round(time.time()-t0, 1), "rows": rows}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "mbpp_history.jsonl").open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    print(f"\npass@1: {score*100:.1f}%  ({len(rows)} tasks, {rec['elapsed_s']}s)")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--mode", choices=["raw", "agent"], default="raw")
    ap.add_argument("--max-steps", type=int, default=8)
    a = ap.parse_args()
    print(f"\n=== MBPP — model={a.model or 'default'} limit={a.limit} mode={a.mode} ===")
    run(a.model, a.limit, a.mode, a.max_steps)


if __name__ == "__main__":
    main()
