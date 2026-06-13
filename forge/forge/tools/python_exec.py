"""
Python execution tool. The single highest-value tool for reasoning + coding
benchmarks: it lets the model *verify its own work* by running code, instead of
guessing. Self-verification is one of the biggest practical gaps between a raw
small model and Sonnet 4.6 — give the model a way to check itself and scores jump.

Runs in a subprocess with a timeout so a bad loop can't hang the agent.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from . import tool


@tool(
    description=(
        "Execute a Python 3 snippet and return its stdout/stderr. Use this to "
        "compute, test code, or verify an answer before finalizing. State does "
        "NOT persist between calls — include everything needed each time."
    ),
    parameters={
        "code": {"type": "string", "description": "Python source to run"},
        "timeout_s": {"type": "integer", "description": "max seconds (default 15)"},
    },
    dangerous=False,
)
def run_python(code: str, timeout_s: int = 15) -> str:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "snippet.py"
        f.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(f)],
                capture_output=True, text=True, timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {timeout_s}s"
        out = (proc.stdout or "")[-4000:]
        err = (proc.stderr or "")[-2000:]
        result = f"exit={proc.returncode}\n--- stdout ---\n{out}"
        if err.strip():
            result += f"\n--- stderr ---\n{err}"
        return result
