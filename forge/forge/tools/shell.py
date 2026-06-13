"""Shell tool. Marked dangerous → the agent confirms before running."""
from __future__ import annotations

import subprocess

from . import tool


@tool(
    description="Run a shell command and return combined stdout/stderr. Use sparingly.",
    parameters={
        "command": {"type": "string", "description": "the command line to execute"},
        "timeout_s": {"type": "integer", "description": "max seconds (default 30)"},
    },
    dangerous=True,
)
def run_shell(command: str, timeout_s: int = 30) -> str:
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return f"ERROR: timed out after {timeout_s}s"
    out = (proc.stdout or "")[-4000:]
    err = (proc.stderr or "")[-2000:]
    return f"exit={proc.returncode}\n{out}\n{err}".strip()
