"""
generate.py — synthesize new coding examples, VERIFY them, keep the good ones (P7).

Pipeline per candidate:
  1. model invents a problem: {instruction, entry, solution, tests}
  2. we actually RUN solution+tests in a subprocess (ground truth, not the model's word)
  3. compute quality (filter.py); store in GoldStore only if passed AND quality>=threshold

The model is the generator; the interpreter is the judge. That asymmetry is what makes
self-generated data trustworthy — we never take the model's claim of correctness, we
execute it. Run: python -m forge.factory.generate --n 20
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ..backend import GenConfig, Message, get_backend
from .filter import PASS_THRESHOLD, estimate_difficulty, quality
from .store import Example, GoldStore

GEN_SYS = """You generate ONE original, self-contained Python coding exercise. Reply with a
single JSON object and nothing else:
{
  "instruction": "<clear problem statement naming the function and behavior>",
  "entry": "<function name>",
  "solution": "<correct Python: imports + the function, real newlines>",
  "tests": "<3-5 assert statements calling <entry> with expected results>"
}
Make it correct and non-trivial but not huge. Vary the topic (strings, lists, math,
dicts, recursion, sorting)."""


def _verify(solution: str, tests: str, entry: str) -> bool:
    if f"def {entry}" not in solution:
        return False
    harness = f"{solution}\n\n{tests}\nprint('GEN_OK')\n"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "g.py"
        f.write_text(harness, encoding="utf-8")
        try:
            p = subprocess.run([sys.executable, str(f)], capture_output=True,
                               text=True, timeout=15)
        except subprocess.TimeoutExpired:
            return False
    return "GEN_OK" in p.stdout


def generate_one(backend, temperature: float = 0.8) -> Example | None:
    raw = backend.chat([Message("system", GEN_SYS), Message("user", "Generate one exercise.")],
                       GenConfig(temperature=temperature, json_mode=True, max_tokens=1200))
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    instr, entry = obj.get("instruction", ""), obj.get("entry", "")
    sol, tests = obj.get("solution", ""), obj.get("tests", "")
    if not all([instr, entry, sol, tests]):
        return None
    passed = _verify(sol, tests, entry)
    q = quality(instr, sol, tests, passed)
    if not passed or q < PASS_THRESHOLD:
        return None
    return Example(instruction=instr, answer=sol, tests=tests,
                   category="coding", difficulty=estimate_difficulty(sol, tests),
                   quality=q, source="factory", verified=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="candidates to attempt")
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    backend = get_backend(a.model)
    store = GoldStore()
    kept = attempts = 0
    print(f"Generating up to {a.n} verified examples (store has {len(store)})...")
    for i in range(a.n):
        attempts += 1
        ex = generate_one(backend)
        if ex and store.add(ex):
            kept += 1
            print(f"  [keep] q={ex.quality} d{ex.difficulty} {ex.instruction[:60]}")
        else:
            print(f"  [drop] candidate {i+1} (failed verify/quality/dup)")
    print(f"\nKept {kept}/{attempts}. Gold store now: {len(store)} examples -> {store.path}")


if __name__ == "__main__":
    main()
