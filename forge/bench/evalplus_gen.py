"""
evalplus_gen.py — generate solutions for HumanEval+ / MBPP+ (EvalPlus).

EvalPlus takes the SAME HumanEval/MBPP problems but adds ~80x more test cases that
catch subtle bugs the originals miss. Strong models that score 90% on HumanEval often
drop 10-20 points on HumanEval+ — it exposes "looks right / memorized but buggy" code.
THIS is the cheapest honesty upgrade.

Division of labor (like SWE-bench): Forge generates the completions here; the official
`evalplus` tool scores them with the PLUS tests.

    pip install evalplus
    python -m bench.evalplus_gen --dataset humaneval --mode raw     # writes samples.jsonl
    evalplus.evaluate --dataset humaneval --samples samples.jsonl   # official PLUS score
    # (use --dataset mbpp for MBPP+)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend, GenConfig, Message  # noqa: E402
from bench.judge import clean_source, _extract_code  # noqa: E402

RAW_SYS = ("You are an expert Python programmer. Complete the function. Reply with ONLY "
           "the complete function (imports + signature + body) in one ```python block.")


def _load(dataset: str):
    if dataset == "humaneval":
        from evalplus.data import get_human_eval_plus
        return get_human_eval_plus()
    from evalplus.data import get_mbpp_plus
    return get_mbpp_plus()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["humaneval", "mbpp"], default="humaneval")
    ap.add_argument("--mode", choices=["raw", "agent"], default="raw")
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default="samples.jsonl")
    a = ap.parse_args()

    backend = get_backend(a.model)
    agent = Agent(backend, max_steps=10) if a.mode == "agent" else None
    problems = _load(a.dataset)
    items = list(problems.items())
    if a.limit:
        items = items[:a.limit]
    print(f"Generating {len(items)} {a.dataset}+ completions ({a.mode})...")

    out, t0 = [], time.time()
    for tid, p in items:
        prompt, entry = p["prompt"], p["entry_point"]
        if a.mode == "raw":
            resp = backend.chat([Message("system", RAW_SYS), Message("user", prompt)],
                                GenConfig(temperature=0.1))
            sol = clean_source([_extract_code(resp), prompt + "\n" + _extract_code(resp)], entry)
        else:
            r = agent.run(f"Complete this function fully and correctly:\n```python\n{prompt}```")
            ex = [s.args.get("code", "") for s in r.steps
                  if s.action == "run_python" and isinstance(s.args, dict)]
            sol = clean_source([_extract_code(r.answer)] + ex, entry)
        out.append({"task_id": tid, "solution": sol or prompt})
        print(f"  {tid}", flush=True)

    Path(a.out).write_text("\n".join(json.dumps(o) for o in out), encoding="utf-8")
    print(f"\nWrote {len(out)} -> {a.out}  ({time.time()-t0:.0f}s)")
    print(f"Score with the OFFICIAL evaluator (gives base AND plus pass@1):")
    print(f"  evalplus.evaluate --dataset {a.dataset} --samples {a.out}")


if __name__ == "__main__":
    main()
