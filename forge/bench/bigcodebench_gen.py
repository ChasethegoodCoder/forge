"""
bigcodebench_gen.py — generate solutions for BigCodeBench.

BigCodeBench is much harder than HumanEval: tasks require composing MULTIPLE real
libraries (numpy, pandas, requests, ...) with rich, precise specs. Top models score far
lower here than on HumanEval — it's a realistic measure of practical coding.

Generate here, score with the official tool:
    pip install bigcodebench
    python -m bench.bigcodebench_gen --mode raw --limit 50
    bigcodebench.evaluate --samples samples_bcb.jsonl --split complete
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend, GenConfig, Message  # noqa: E402
from bench.judge import _extract_code  # noqa: E402

RAW_SYS = ("Expert Python programmer. Complete the function using the libraries the "
           "docstring requires. Reply with ONLY the full function in one ```python block.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["raw", "agent"], default="raw")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--split", default="complete", choices=["complete", "instruct"])
    ap.add_argument("--out", default="samples_bcb.jsonl")
    a = ap.parse_args()

    from datasets import load_dataset
    ds = load_dataset("bigcode/bigcodebench", split="v0.1.2")
    rows = list(ds)
    if a.limit:
        rows = rows[:a.limit]

    backend = get_backend(a.model)
    agent = Agent(backend, max_steps=12) if a.mode == "agent" else None
    print(f"Generating {len(rows)} BigCodeBench ({a.split}) completions ({a.mode})...")

    out, t0 = [], time.time()
    for r in rows:
        prompt = r["complete_prompt"] if a.split == "complete" else r["instruct_prompt"]
        if a.mode == "raw":
            resp = backend.chat([Message("system", RAW_SYS), Message("user", prompt)],
                                GenConfig(temperature=0.1, max_tokens=1024))
            sol = _extract_code(resp)
        else:
            res = agent.run(f"Complete this Python function fully:\n```python\n{prompt}```")
            sol = _extract_code(res.answer)
        out.append({"task_id": r["task_id"], "solution": sol})
        print(f"  {r['task_id']}", flush=True)

    Path(a.out).write_text("\n".join(json.dumps(o) for o in out), encoding="utf-8")
    print(f"\nWrote {len(out)} -> {a.out}  ({time.time()-t0:.0f}s)")
    print("Score: bigcodebench.evaluate --samples %s --split %s" % (a.out, a.split))


if __name__ == "__main__":
    main()
