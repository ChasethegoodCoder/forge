"""
improve.py — the continuous self-improvement loop (Phase 8/10 / #21).

One cycle of the flywheel:
  1. GENERATE   verified examples -> GoldStore           (works now)
  2. PREPARE    GoldStore -> chat-format train data       (works now)
  3. TRAIN      QLoRA adapter on the data                 (needs deps + GPU time)
  4. EVAL-GATE  new model vs current on held-out HumanEval; PROMOTE only if better
  5. REPEAT

Steps 1-2 run today. Steps 3-4 are gated on training deps so the loop never
half-breaks. The eval gate is the safety rail: a new checkpoint replaces the default
ONLY if it measurably beats the current one — no silent regressions, no benchmark
overfitting (held-out split). Run: python -m forge.improve --generate 50
"""
from __future__ import annotations

import argparse

from .factory.generate import generate_one
from .factory.store import GoldStore
from .backend import get_backend


def cycle(generate_n: int, eval_limit: int) -> None:
    print("=== Forge improvement cycle ===")

    # 1. GENERATE
    backend = get_backend()
    store = GoldStore()
    before = len(store)
    print(f"[1/4] generating up to {generate_n} verified examples (store={before})...")
    kept = 0
    for _ in range(generate_n):
        ex = generate_one(backend)
        if ex and store.add(ex):
            kept += 1
    print(f"      kept {kept} new; store now {len(store)}")

    # 2. PREPARE
    print("[2/4] preparing training data...")
    from .train.prepare import main as prepare_main
    import sys
    sys.argv = ["prepare"]
    try:
        prepare_main()
    except SystemExit:
        pass

    # 3. TRAIN (gated)
    print("[3/4] training (QLoRA)...")
    from .train.qlora import _check_deps
    problem = _check_deps()
    if problem:
        print("      SKIPPED — " + problem.splitlines()[0])
        print("      (install training deps + commit GPU time to enable steps 3-4)")
        _explain_gate(eval_limit)
        return
    from .train.qlora import train, DEFAULTS
    train(DEFAULTS)

    # 4. EVAL-GATE + PROMOTE
    print("[4/4] eval-gated promotion...")
    _explain_gate(eval_limit)
    print("      (wire adapter -> GGUF -> `ollama create forge-candidate`, then compare)")


def _explain_gate(eval_limit: int) -> None:
    print(f"      GATE: run held-out HumanEval (limit={eval_limit}) on candidate vs "
          f"current; promote candidate to config.engine.model ONLY if pass@1 rises "
          f"beyond the noise floor. Keep base as fallback.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", type=int, default=30, help="examples to attempt this cycle")
    ap.add_argument("--eval-limit", type=int, default=40, help="held-out eval size")
    a = ap.parse_args()
    cycle(a.generate, a.eval_limit)


if __name__ == "__main__":
    main()
