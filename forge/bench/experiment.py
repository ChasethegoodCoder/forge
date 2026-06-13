"""
experiment.py — Research Mode (Phase 10 / #22): hypothesis -> A/B -> verdict.

Formalizes what we keep doing by hand: state a hypothesis, run two arms under
identical conditions, compare on the benchmark, and log a verdict. This is how the
project decides what actually works instead of guessing. Every experiment is recorded
to bench/results/experiments.jsonl so the history of "what we tried and learned" is
durable.

Example:
  python -m bench.experiment --name critic_vs_agent \\
    --hypothesis "critic mode beats agent on coding" \\
    --arm-a mode=agent --arm-b mode=critic --limit 20
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bench.humaneval import run as he_run  # noqa: E402

LOG = Path(__file__).resolve().parent / "results" / "experiments.jsonl"


def _parse_arm(pairs: list[str]) -> dict:
    """Turn ['mode=critic','model=qwen2.5:7b'] into a kwargs dict for he_run."""
    arm = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        arm[k.strip()] = v.strip()
    return arm


def _run_arm(arm: dict, limit: int, k: int) -> dict:
    rec = he_run(model=arm.get("model"), limit=limit, k=k,
                 max_steps=int(arm.get("max_steps", 10)), mode=arm.get("mode", "agent"))
    return {"pass1": rec["pass1"], "passk": rec["passk"],
            "elapsed_s": rec["elapsed_s"], "mode": rec["mode"], "model": rec["model"]}


def run_experiment(name: str, hypothesis: str, arm_a: dict, arm_b: dict,
                   limit: int, k: int) -> dict:
    t0 = time.time()
    print(f"\n=== EXPERIMENT: {name} ===\nHypothesis: {hypothesis}")
    print(f"-- Arm A: {arm_a}"); a = _run_arm(arm_a, limit, k)
    print(f"-- Arm B: {arm_b}"); b = _run_arm(arm_b, limit, k)

    delta = round((b["pass1"] - a["pass1"]) * 100, 1)
    # honest verdict: needs a real margin (one problem on n=20 is 5pts of noise)
    noise = 100.0 / max(limit, 1)
    if abs(delta) <= noise:
        verdict = f"INCONCLUSIVE (Δ={delta:+.1f}pts within ~{noise:.1f}pt noise floor)"
    else:
        winner = "B" if delta > 0 else "A"
        verdict = f"Arm {winner} wins (Δ={delta:+.1f}pts)"

    rec = {
        "ts": datetime.now(timezone.utc).isoformat(), "name": name,
        "hypothesis": hypothesis, "limit": limit, "k": k,
        "arm_a": {**arm_a, **a}, "arm_b": {**arm_b, **b},
        "delta_pts": delta, "verdict": verdict, "elapsed_s": round(time.time() - t0, 1),
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.open("a", encoding="utf-8").write(json.dumps(rec) + "\n")
    print(f"\nA pass@1={a['pass1']*100:.1f}%  B pass@1={b['pass1']*100:.1f}%")
    print(f"VERDICT: {verdict}\nlogged -> {LOG}")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--hypothesis", default="")
    ap.add_argument("--arm-a", nargs="*", default=["mode=agent"])
    ap.add_argument("--arm-b", nargs="*", default=["mode=raw"])
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--k", type=int, default=1)
    a = ap.parse_args()
    run_experiment(a.name, a.hypothesis, _parse_arm(a.arm_a), _parse_arm(a.arm_b),
                   a.limit, a.k)


if __name__ == "__main__":
    main()
