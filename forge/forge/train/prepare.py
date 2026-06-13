"""
prepare.py — turn the GoldStore into a training file (pure code, no GPU).

Converts verified examples into chat-format JSONL that the QLoRA trainer consumes.
Two sources of data, both already verified:
  - factory output (data/gold/examples.jsonl)
  - benchmark wins/failures can be added later (mine traces -> gold)

Keeps only quality>=threshold, shuffles deterministically, and writes a train/val split.
Run: python -m forge.train.prepare
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from ..factory.store import GoldStore

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "train"

SYS = ("You are an expert Python programmer. Write correct, clean code that solves "
       "the user's request.")


def to_chat(ex: dict) -> dict:
    """One example -> chat sample. Trainer applies the model's chat template."""
    answer = ex["answer"].strip()
    if "```" not in answer:
        answer = f"```python\n{answer}\n```"
    return {"messages": [
        {"role": "system", "content": SYS},
        {"role": "user", "content": ex["instruction"].strip()},
        {"role": "assistant", "content": answer},
    ]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-quality", type=float, default=0.7)
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    rows = [e for e in GoldStore().all()
            if e.get("verified") and e.get("quality", 0) >= a.min_quality]
    if not rows:
        print("No qualifying examples yet. Run: python -m forge.factory.generate --n 50")
        return
    random.Random(a.seed).shuffle(rows)
    n_val = max(1, int(len(rows) * a.val_frac)) if len(rows) > 10 else 0
    val, train = rows[:n_val], rows[n_val:]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, split in (("train", train), ("val", val)):
        if not split:
            continue
        p = OUT_DIR / f"{name}.jsonl"
        p.write_text("\n".join(json.dumps(to_chat(e)) for e in split), encoding="utf-8")
        print(f"wrote {len(split)} -> {p}")
    print(f"\nTotal {len(rows)} examples ready. Next: python -m forge.train.qlora")


if __name__ == "__main__":
    main()
