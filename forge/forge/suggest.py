"""
suggest.py - autonomous improvement suggestions (Phase 10 / #23).

Reads every results ledger + the gold store and proposes a RANKED, data-driven list of
what to do next - the lowest-scoring suite, the biggest gap to target, whether there's
enough data to fine-tune, what experiments haven't been tried. This turns "what should I
work on?" into a question answered by the numbers, not a hunch. Pairs with research mode
(experiment.py) which then tests the suggestions.

  python -m forge.suggest   (or: python cli.py suggest)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
RESULTS = Path(__file__).resolve().parent.parent / "bench" / "results"
TARGET = 0.92


def _load(name: str) -> list[dict]:
    f = RESULTS / name
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if f.exists() else []


def suggestions() -> list[tuple[int, str, str]]:
    """Return (priority, action, rationale) sorted by priority desc."""
    out: list[tuple[int, str, str]] = []
    suite = _load("history.jsonl")
    he = _load("humaneval_history.jsonl")

    # 1) lowest-scoring suite = where to focus
    if suite:
        cats = suite[-1].get("by_category", {})
        if cats:
            worst, score = min(cats.items(), key=lambda kv: kv[1])
            gap = int((1 - score) * 100)
            out.append((90 + gap // 10,
                        f"Improve the '{worst}' suite (now {score*100:.0f}%)",
                        f"It's the lowest category - biggest headroom. Try --mode bestofn "
                        f"or --mode critic on it, then fine-tune on mined '{worst}' failures."))

    # 2) gap to target on HumanEval
    if he:
        now = he[-1]["pass1"]
        gap = (TARGET - now) * 100
        if gap > 2:
            out.append((70, f"Close the {gap:.0f}-pt HumanEval gap to Sonnet 4.6",
                        f"At {now*100:.0f}% vs {TARGET*100:.0f}%. Harder benchmarks + critic; "
                        f"consider a 14B base if latency is acceptable."))

    # 3) data readiness for fine-tuning
    try:
        from forge.factory.store import GoldStore
        n = len(GoldStore())
    except Exception:
        n = 0
    if n < 200:
        out.append((85, f"Grow the gold dataset ({n} -> 200+ examples)",
                    "Fine-tuning needs hundreds of verified examples to beat the eval-gate. "
                    "Run: python -m forge.factory.generate --n 200 && python -m forge.mine"))
    else:
        out.append((80, f"Fine-tune on {n} examples (enough to try)",
                    "Dataset is large enough. Run qlora + eval_gate; promote only if it wins."))

    # 4) experiments not yet run
    exps = {e.get("name") for e in _load("experiments.jsonl")}
    for name, why in [
        ("bestofn_vs_single", "Does best-of-N beat a single pass on the agent suite?"),
        ("critic_vs_single", "Quantify the critic's value on coding/agent."),
        ("planner_on_off", "Does the planner stage help multi-step tasks?"),
    ]:
        if name not in exps:
            out.append((60, f"Run experiment: {name}", why + " (use bench/experiment.py)"))

    # 5) multi-file coverage
    if len(_load("repobench_history.jsonl")) and len(_load("repobench_history.jsonl")) < 3:
        out.append((50, "Expand RepoBench beyond 3 tasks",
                    "Small n; add multi-file tasks so harness gains are statistically visible."))

    out.sort(key=lambda x: x[0], reverse=True)
    return out


def main():
    s = suggestions()
    if not s:
        print("No data yet - run `python cli.py bench` and `humaneval` first.")
        return
    print("=== Forge - data-driven improvement suggestions ===\n")
    for i, (pri, action, why) in enumerate(s, 1):
        print(f"{i}. [{pri}] {action}\n     {why}\n")


if __name__ == "__main__":
    main()
