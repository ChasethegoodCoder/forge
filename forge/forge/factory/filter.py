"""
filter.py — quality gate for generated examples (pure, deterministic).

The factory generates a lot of candidates; most should be rejected. A noisy training
set hurts more than a small clean one, so this gate is strict. Quality is only
computed for examples that ALREADY passed their tests (verified=True is a hard
prerequisite, enforced upstream). Here we score the *teaching value* of a verified
example so the best rise to the top.
"""
from __future__ import annotations

import ast
import re


def estimate_difficulty(code: str, tests: str) -> int:
    """Rough 1..5 from structure: control flow, helpers, recursion, data structures."""
    score = 1
    score += code.count("for") + code.count("while")           # loops
    score += 2 * len(re.findall(r"\bdef \w+", code)[1:])        # helper functions
    score += 2 if re.search(r"\b(\w+)\s*\(.*\)\s*$", code) and "return" in code and \
        re.search(r"def (\w+).*\1\(", code, re.DOTALL) else 0   # recursion-ish
    score += 1 if re.search(r"\b(dict|set|deque|heapq|defaultdict)\b", code) else 0
    score += tests.count("assert") // 3
    return max(1, min(5, score))


def quality(instruction: str, code: str, tests: str, passed: bool) -> float:
    """0..1 teaching-quality score. Passing tests is a hard gate (0 if it failed)."""
    if not passed:
        return 0.0
    try:
        ast.parse(code)
    except SyntaxError:
        return 0.0

    q = 0.5  # baseline for verified, compilable code
    # has a real function definition
    if re.search(r"\bdef \w+\s*\(", code):
        q += 0.1
    # has a docstring (teaches intent)
    if re.search(r'def \w+\([^)]*\):\s*("""|\'\'\')', code):
        q += 0.1
    # reasonable size (not trivial, not bloated)
    nlines = len([l for l in code.splitlines() if l.strip()])
    if 3 <= nlines <= 40:
        q += 0.1
    # instruction is specific enough
    if len(instruction.split()) >= 6:
        q += 0.1
    # multiple asserts = stronger verification
    if tests.count("assert") >= 3:
        q += 0.1
    # penalties for anti-patterns
    if "eval(" in code or "exec(" in code:
        q -= 0.3
    if "TODO" in code or "pass" == code.strip():
        q -= 0.2
    return round(max(0.0, min(1.0, q)), 3)


PASS_THRESHOLD = 0.7  # only examples at/above this enter the gold store
