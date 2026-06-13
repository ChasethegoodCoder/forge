"""
report.py — render the progress ledger (results/history.jsonl) as a table so you
can SEE the gap to the target closing (or not). Prints overall + per-category
scores per run, and the delta from the previous run.
"""
from __future__ import annotations

import json
from pathlib import Path

HISTORY = Path(__file__).resolve().parent / "results" / "history.jsonl"

# Phase 1 target anchors (see docs/PHASE2_TARGET_ANALYSIS.md). These are the
# benchmark scores we ASSUME Sonnet 4.6 would get on THIS suite (near-ceiling).
TARGET = {"overall": 0.98}


def load() -> list[dict]:
    if not HISTORY.exists():
        return []
    return [json.loads(l) for l in HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    runs = load()
    if not runs:
        print("No benchmark runs yet. Run:  python cli.py bench")
        return
    print(f"\n=== Forge Progress Ledger ({len(runs)} runs) ===")
    print(f"{'when':<20} {'model':<26} {'overall':>8} {'vs target':>10} {'delta':>7}")
    prev = None
    for r in runs:
        when = r["ts"][:19].replace("T", " ")
        ov = r["overall"]
        gap = TARGET["overall"] - ov
        delta = "" if prev is None else f"{(ov - prev)*100:+.1f}"
        print(f"{when:<20} {r['model']:<26} {ov*100:>7.1f}% {gap*100:>9.1f}% {delta:>7}")
        prev = ov

    last = runs[-1]
    print("\nLatest by category:")
    for cat, v in last.get("by_category", {}).items():
        print(f"  {cat:<12} {v*100:5.1f}%")
    print(f"\nTarget (assumed Sonnet 4.6 on this suite): {TARGET['overall']*100:.0f}%")
    print(f"Current gap to target: {(TARGET['overall']-last['overall'])*100:.1f} points")


if __name__ == "__main__":
    main()
