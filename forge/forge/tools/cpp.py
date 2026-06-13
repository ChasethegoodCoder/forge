"""
cpp.py — compile & run C++ so the agent can VERIFY C++ (not just write it).

Forge's verify-loop was Python-only (run_python). This adds the same self-check for
C++: write source, compile with g++, run, return output. Now the agent can iterate on
C++ until it actually compiles and passes — the same discipline that makes it strong at
Python. Requires g++ on the machine (present on most Linux/rented boxes; on Windows
install MinGW or run on the rented box).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import tool


@tool(
    description=(
        "Compile and run a C++ program (C++17). Returns compiler errors or program "
        "stdout/stderr. Use this to VERIFY C++ you wrote actually compiles and works "
        "before finalizing — the same way run_python verifies Python."
    ),
    parameters={
        "code": {"type": "string", "description": "full C++ source (include main())"},
        "stdin": {"type": "string", "description": "optional input fed to the program"},
        "timeout_s": {"type": "integer", "description": "max seconds (default 15)"},
    },
)
def run_cpp(code: str, stdin: str = "", timeout_s: int = 15) -> str:
    gpp = shutil.which("g++") or shutil.which("clang++")
    if not gpp:
        return "ERROR: no C++ compiler (g++/clang++) found on this machine."
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "main.cpp"
        exe = Path(d) / "a.out"
        src.write_text(code, encoding="utf-8")
        comp = subprocess.run([gpp, "-std=c++17", "-O2", str(src), "-o", str(exe)],
                              capture_output=True, text=True, timeout=60)
        if comp.returncode != 0:
            return f"COMPILE ERROR:\n{comp.stderr[-2500:]}"
        try:
            run = subprocess.run([str(exe)], input=stdin, capture_output=True,
                                 text=True, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            return f"ERROR: program timed out after {timeout_s}s"
        out = (run.stdout or "")[-3000:]
        err = (run.stderr or "")[-1500:]
        res = f"compiled OK, exit={run.returncode}\n--- stdout ---\n{out}"
        if err.strip():
            res += f"\n--- stderr ---\n{err}"
        return res
