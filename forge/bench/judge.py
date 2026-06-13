"""
judge.py — automated, objective scoring. No LLM-judge needed for these task
types, which keeps measurement cheap, fast, and deterministic (critical: if your
ruler is noisy you can't tell whether the model improved or the judge wandered).

Scorers:
  numeric    — extract a number from the answer, compare within tolerance
  exact      — normalized string equality
  contains   — expected substring present (case-insensitive)
  code_test  — extract a code block, run the provided asserts in a subprocess
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_CODE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _extract_number(text: str):
    m = _NUM_RE.findall(text.replace(",", ""))
    return float(m[-1]) if m else None


def _repair(code: str) -> str:
    """Fix common small-model artifacts so source is runnable."""
    code = code.strip()
    # literal escape sequences instead of real newlines
    if "\n" not in code and ("\\n" in code or "\\t" in code):
        try:
            code = code.encode("utf-8").decode("unicode_escape")
        except (UnicodeDecodeError, ValueError):
            pass
    return code


def _extract_code(text: str) -> str:
    blocks = _CODE_RE.findall(text)
    if blocks:
        # prefer blocks that actually define something over example/REPL blocks
        defs = [b for b in blocks if re.search(r"\b(def|class|import|from)\b", b)]
        return _repair("\n\n".join(defs or blocks))
    return _repair(text)


def _pick_source(answer: str, entry: str, extra_code: list[str]) -> str:
    """Choose runnable source that defines `entry`. Prefer the final answer, but
    fall back to code the agent executed during the run (where the real working
    definition usually lives, even if the prose answer is malformed)."""
    final_code = _extract_code(answer)
    candidates = [final_code] + [_repair(c) for c in extra_code]
    pat = re.compile(rf"\b(def|class)\s+{re.escape(entry)}\b|\b{re.escape(entry)}\s*=")
    for c in candidates:
        if pat.search(c):
            return c
    return final_code


def clean_source(candidates: list[str], entry: str) -> str:
    """AST-normalize messy model output into clean, compilable source defining
    `entry`. Keeps only imports + defs + assigns; drops duplicate bodies, stray
    statements, and self-imports. The robust scorer used by ALL code tasks. Returns
    "" if no candidate (raw or escape-repaired) parses and defines entry."""
    import ast
    KEEP = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
            ast.ClassDef, ast.Assign)
    for raw in candidates:
        if not raw or not raw.strip():
            continue
        for variant in (raw, _repair(raw)):
            try:
                tree = ast.parse(variant)
            except SyntaxError:
                continue
            body, names = [], set()
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mods = [a.name for a in node.names]
                    if "solution" in mods or getattr(node, "module", "") == "solution":
                        continue
                    body.append(node)
                elif isinstance(node, KEEP):
                    body.append(node)
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        names.add(node.name)
            if entry in names:
                return ast.unparse(ast.Module(body=body, type_ignores=[]))
    return ""


def score_one(answer: str, spec: dict, extra_code: list[str] | None = None) -> tuple[float, str]:
    """Return (score in [0,1], note). `extra_code` is code the agent executed
    during the run, used as a fallback source for code_test scoring."""
    t = spec["type"]

    if t == "numeric":
        got = _extract_number(answer)
        if got is None:
            return 0.0, "no number found"
        ok = abs(got - float(spec["expected"])) <= float(spec.get("tol", 0))
        return (1.0 if ok else 0.0), f"got {got}, expected {spec['expected']}"

    if t == "exact":
        return (1.0 if _norm(answer) == _norm(str(spec["expected"])) else 0.0), ""

    if t == "contains":
        return (1.0 if _norm(str(spec["expected"])) in _norm(answer) else 0.0), ""

    if t == "code_test":
        entry = spec.get("entry", "")
        # robust: AST-normalize final answer + executed snippets into clean source
        candidates = [_extract_code(answer)] + (extra_code or [])
        code = clean_source(candidates, entry)
        if not code:
            return 0.0, f"no compilable solution defining {entry}"
        harness = f"{code}\n\n{spec['tests']}\nprint('ALL_TESTS_PASSED')\n"
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "t.py"
            f.write_text(harness, encoding="utf-8")
            try:
                proc = subprocess.run([sys.executable, str(f)],
                                      capture_output=True, text=True, timeout=20)
            except subprocess.TimeoutExpired:
                return 0.0, "timeout"
        if "ALL_TESTS_PASSED" in proc.stdout:
            return 1.0, "tests passed"
        err = (proc.stderr or "").strip().splitlines()
        return 0.0, "FAIL: " + (err[-1] if err else "no output")

    return 0.0, f"unknown scorer {t}"
