"""
eval_gate.py — did fine-tuning actually help? (Phase 8 safety rail)

Runs the SAME HumanEval problems on the base model and on base+adapter, compares
pass@1, and gives a PROMOTE / REJECT verdict with a noise floor. This is the rule that
keeps the project honest: a new checkpoint is only worth keeping if it MEASURABLY beats
the base on held-out problems. No vibes, no "it feels smarter."

Runs base then adapter sequentially (frees VRAM between) so two 7Bs don't collide.
  python -m forge.train.eval_gate --limit 20 --offset 100   # held-out slice
"""
from __future__ import annotations

import argparse
import gc
from pathlib import Path

ADAPTER = Path(__file__).resolve().parent.parent.parent / "adapters"


def _eval(backend, problems) -> float:
    from bench.humaneval import solve_raw
    passes = sum(solve_raw(backend, p)[0] for p in problems)
    return passes / len(problems)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--offset", type=int, default=100, help="held-out: skip first N problems")
    a = ap.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from bench.humaneval import load_problems
    import torch
    from forge.hf_backend import HFBackend

    # held-out slice the model was NOT trained on
    problems = load_problems(a.offset + a.limit)[a.offset:]
    if not problems:
        print("No held-out problems in that range; lower --offset.")
        return
    print(f"Held-out eval on {len(problems)} problems (offset {a.offset})\n")

    print("== base ==")
    base = HFBackend(base_model=a.base, adapter=None)
    base_score = _eval(base, problems)
    del base; gc.collect(); torch.cuda.empty_cache()

    print("== base + adapter ==")
    tuned = HFBackend(base_model=a.base, adapter=str(ADAPTER))
    tuned_score = _eval(tuned, problems)
    del tuned; gc.collect(); torch.cuda.empty_cache()

    delta = (tuned_score - base_score) * 100
    noise = 100.0 / len(problems)
    print(f"\nbase    pass@1: {base_score*100:.1f}%")
    print(f"tuned   pass@1: {tuned_score*100:.1f}%")
    print(f"delta: {delta:+.1f} pts  (noise floor ~{noise:.1f})")
    if delta > noise:
        print("VERDICT: PROMOTE — tuned model beats base. Convert adapter to GGUF, "
              "`ollama create forge-v1`, set engine.model in forge.yaml.")
    else:
        print("VERDICT: REJECT — not better than base beyond noise. Keep base; gather "
              "more/better training data and try again. (This is the system working.)")


if __name__ == "__main__":
    main()
