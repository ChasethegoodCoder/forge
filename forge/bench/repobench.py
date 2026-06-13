"""
repobench.py — multi-file "fix the bug" benchmark (Phase 15, SWE-bench-style).

THIS is the benchmark where the harness should pull ahead of the raw model. Each
task drops a small multi-file project (with a bug) into the workspace; the agent must
EXPLORE it (glob/grep/read), LOCATE the bug across files, EDIT surgically (edit_file),
and VERIFY (run_python) until a hidden test passes. A single-pass raw model can't do
this — it needs the tools and the loop. That's the whole point of measuring here.

Scoring: after the agent runs, we execute the task's test with cwd = the project dir.
Pass = the test runs green. No code extraction — we test the files on disk.

Run: python -m bench.repobench                 (agent mode, all tasks)
     python -m bench.repobench --mode raw       (baseline: raw model, no tools)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend  # noqa: E402
from forge.tools.files import WORKSPACE  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"

# Each task: a mini-repo (files), a natural-language bug report, and a hidden test.
TASKS = [
    {
        "id": "repo-001",
        "report": "apply_discount(price, pct) should REDUCE price by the given fraction "
                  "(e.g. 10% off 100 = 90), but it's returning the wrong number. Find and fix the bug.",
        "files": {
            "utils.py": "def round2(x):\n    return round(x, 2)\n",
            "discount.py": "from utils import round2\n\n"
                           "def apply_discount(price, pct):\n"
                           "    # reduce price by pct fraction\n"
                           "    return round2(price + price * pct)\n",
        },
        "test": "from discount import apply_discount\n"
                "assert apply_discount(100, 0.1) == 90.0\n"
                "assert apply_discount(50, 0.5) == 25.0\n",
    },
    {
        "id": "repo-002",
        "report": "total_pages(items, per_page) should return how many pages are needed, "
                  "rounding UP (5 items, 2 per page = 3 pages). It under-counts. Fix it.",
        "files": {
            "paging.py": "def total_pages(items, per_page):\n"
                         "    # number of pages needed to show all items\n"
                         "    return len(items) // per_page\n",
        },
        "test": "from paging import total_pages\n"
                "assert total_pages([1,2,3,4,5], 2) == 3\n"
                "assert total_pages([], 2) == 0\n"
                "assert total_pages([1,2], 2) == 1\n",
    },
    {
        "id": "repo-003",
        "report": "In stats.py, median() returns wrong results. mean() and mode() are fine — "
                  "only median is broken (it doesn't sort and mishandles even-length lists). Fix median().",
        "files": {
            "stats.py": "def mean(xs):\n    return sum(xs) / len(xs)\n\n"
                        "def median(xs):\n"
                        "    n = len(xs)\n"
                        "    mid = n // 2\n"
                        "    return xs[mid]\n\n"
                        "def mode(xs):\n"
                        "    return max(set(xs), key=xs.count)\n",
        },
        "test": "from stats import median\n"
                "assert median([3,1,2]) == 2\n"
                "assert median([1,2,3,4]) == 2.5\n"
                "assert median([5]) == 5\n",
    },
    {
        "id": "repo-004",
        "report": "final_price(p) should apply the DISCOUNT from config as a REDUCTION "
                  "(20% off 100 = 80), but it returns the wrong amount. Fix it.",
        "files": {
            "config.py": "DISCOUNT = 0.2\n",
            "pricing.py": "from config import DISCOUNT\n\n"
                          "def final_price(p):\n    return p * DISCOUNT\n",
        },
        "test": "from pricing import final_price\n"
                "assert final_price(100) == 80\n"
                "assert final_price(50) == 40\n",
    },
    {
        "id": "repo-005",
        "report": "valid_password(s) should accept passwords of length >= MIN_LEN (8), "
                  "but it rejects passwords that are exactly 8 chars. Fix the boundary.",
        "files": {
            "rules.py": "MIN_LEN = 8\n",
            "validate.py": "from rules import MIN_LEN\n\n"
                           "def valid_password(s):\n    return len(s) > MIN_LEN\n",
        },
        "test": "from validate import valid_password\n"
                "assert valid_password('a'*8) == True\n"
                "assert valid_password('a'*7) == False\n",
    },
    {
        "id": "repo-006",
        "report": "normalize(x) should clamp x into [0, 100], but values above 100 aren't "
                  "capped. The bug is in the clamp() helper. Fix it.",
        "files": {
            "helpers.py": "def clamp(x, lo, hi):\n    return max(lo, x)\n",
            "main.py": "from helpers import clamp\n\n"
                       "def normalize(x):\n    return clamp(x, 0, 100)\n",
        },
        "test": "from main import normalize\n"
                "assert normalize(150) == 100\n"
                "assert normalize(-5) == 0\n"
                "assert normalize(50) == 50\n",
    },
    {
        "id": "repo-007",
        "report": "word_count(text) miscounts when there are multiple spaces between words "
                  "(it counts empty strings). The bug is in how analyzer.py splits. Fix it.",
        "files": {
            "text_utils.py": "def clean(text):\n    return text.strip()\n",
            "analyzer.py": "from text_utils import clean\n\n"
                           "def word_count(text):\n    return len(clean(text).split(' '))\n",
        },
        "test": "from analyzer import word_count\n"
                "assert word_count('hello  world') == 2\n"
                "assert word_count('a b c') == 3\n"
                "assert word_count('  spaced   out  ') == 2\n",
    },
]

PROMPT = """There is a small Python project in the folder `{dir}/` in your workspace.

{report}

Steps: use glob_files/grep/read_file to explore `{dir}/`, find the bug, fix it with
edit_file, and verify with run_python. Do NOT rewrite whole files unless necessary —
make a surgical edit. The fix must be saved in the project files."""


def _setup(task: dict) -> Path:
    d = WORKSPACE / task["id"]
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)  # tolerate Windows pycache locks
    d.mkdir(parents=True, exist_ok=True)
    for name, content in task["files"].items():
        (d / name).write_text(content, encoding="utf-8")
    return d


def _score(task: dict, proj: Path) -> tuple[bool, str]:
    # clear any stale bytecode so we test the CURRENT source, not a cached .pyc
    pycache = proj / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache, ignore_errors=True)
    runner = proj / "_test.py"
    runner.write_text(task["test"] + "\nprint('REPO_OK')\n", encoding="utf-8")
    try:
        p = subprocess.run([sys.executable, "-B", "_test.py"], cwd=str(proj),
                           capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    finally:
        if runner.exists():
            runner.unlink()
    if "REPO_OK" in p.stdout:
        return True, "tests pass"
    err = (p.stderr or "").strip().splitlines()
    return False, (err[-1] if err else "fail")[:80]


def run(model: str | None, mode: str, max_steps: int) -> dict:
    backend = get_backend(model)
    agent = Agent(backend, max_steps=max_steps) if mode != "raw" else None
    rows = []
    t0 = time.time()
    for task in TASKS:
        proj = _setup(task)
        ts = time.time()
        if mode == "raw":
            # raw baseline: one shot, no tools — show the file, ask for the fix
            from forge.backend import Message, GenConfig
            fname = list(task["files"])[0]
            content = "\n\n".join(f"# {n}\n{c}" for n, c in task["files"].items())
            out = backend.chat([
                Message("system", "You are an expert Python debugger. Output the corrected "
                        "full content of the file that needs fixing, in one ```python block."),
                Message("user", f"{task['report']}\n\nProject files:\n{content}")],
                GenConfig(temperature=0.1))
            import re
            m = re.search(r"```(?:python)?\s*(.*?)```", out, re.DOTALL)
            if m:
                (proj / fname).write_text(m.group(1), encoding="utf-8")
        else:
            agent.run(PROMPT.format(dir=task["id"], report=task["report"]))
        ok, note = _score(task, proj)
        dt = round(time.time() - ts, 1)
        rows.append({"id": task["id"], "pass": int(ok), "secs": dt, "note": note})
        print(f"  [{'PASS' if ok else 'FAIL'}] {task['id']:<9} {dt:>5}s  {note}", flush=True)

    score = sum(r["pass"] for r in rows) / len(rows)
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "bench": "RepoBench",
           "model": backend.name, "mode": mode, "n": len(rows),
           "score": round(score, 4), "elapsed_s": round(time.time() - t0, 1), "rows": rows}
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "repobench_history.jsonl").open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    ap.add_argument("--mode", choices=["raw", "agent"], default="agent")
    ap.add_argument("--max-steps", type=int, default=12)
    a = ap.parse_args()
    print(f"\n=== RepoBench (multi-file) — model={a.model or 'default'} mode={a.mode} ===")
    rec = run(a.model, a.mode, a.max_steps)
    print(f"\nscore: {rec['score']*100:.1f}%  ({rec['n']} tasks, {rec['elapsed_s']}s)")
    print("logged -> bench/results/repobench_history.jsonl")


if __name__ == "__main__":
    main()
