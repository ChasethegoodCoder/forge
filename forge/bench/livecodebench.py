"""
livecodebench.py — generate solutions for LiveCodeBench (the contamination-proof one).

LiveCodeBench continuously collects NEW competitive-programming problems with release
dates. By evaluating ONLY on problems published AFTER a model's training cutoff, you
guarantee it couldn't have memorized them — so the score is the model's REAL ability,
not recall. This is the number to trust most.

    pip install datasets
    python -m bench.livecodebench --after 2025-01-01 --mode agent --limit 30
    # then score with the official LiveCodeBench runner (handles their test format):
    #   https://github.com/LiveCodeBench/LiveCodeBench  (lcb_runner)

Use --after = your model's training cutoff (e.g. Qwen2.5 ~2024 -> use 2025-01-01).
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

SYS = ("Expert competitive programmer. Read the problem, write a correct, efficient "
       "Python solution that reads stdin and writes stdout exactly as specified. Reply "
       "with ONLY the full program in one ```python block.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--after", default="2025-01-01",
                    help="only problems released after this date (contamination-free)")
    ap.add_argument("--mode", choices=["raw", "agent"], default="agent")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--out", default="samples_lcb.jsonl")
    a = ap.parse_args()

    from datasets import load_dataset
    ds = load_dataset("livecodebench/code_generation_lite", split="test",
                      version_tag="release_latest", trust_remote_code=True)
    rows = [r for r in ds if str(r.get("contest_date", "")) >= a.after]
    rows = rows[:a.limit] if a.limit else rows
    print(f"{len(rows)} contamination-free problems (after {a.after})")

    backend = get_backend(a.model)
    agent = Agent(backend, max_steps=12) if a.mode == "agent" else None
    out, t0 = [], time.time()
    for r in rows:
        q = r.get("question_content", "")[:6000]
        if a.mode == "raw":
            resp = backend.chat([Message("system", SYS), Message("user", q)],
                                GenConfig(temperature=0.2, max_tokens=2048))
            sol = _extract_code(resp)
        else:
            res = agent.run(f"Solve this competitive programming problem (read stdin, "
                            f"write stdout):\n\n{q}")
            sol = _extract_code(res.answer)
        out.append({"question_id": r.get("question_id"), "code_list": [sol]})
        print(f"  {r.get('question_id')}", flush=True)

    Path(a.out).write_text("\n".join(json.dumps(o) for o in out), encoding="utf-8")
    print(f"\nWrote {len(out)} -> {a.out}  ({time.time()-t0:.0f}s)")
    print("Score with the official LiveCodeBench lcb_runner (it runs the hidden tests).")


if __name__ == "__main__":
    main()
