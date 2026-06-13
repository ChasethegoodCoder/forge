"""
code.py — Claude-Code-style code-navigation & editing tools.

This is the heart of "porting the harness": the reason Claude Code edits real
codebases well is NOT a bigger model — it's having `grep`, `glob`, and a *surgical*
`edit` (exact string replace) instead of only whole-file writes. These three tools
give Forge the same multi-file capability. Sandboxed to the workspace, like files.py.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import tool
from .files import WORKSPACE, _safe


@tool(
    description=(
        "Surgical edit: replace an EXACT substring in a file with new text. "
        "`old` must appear exactly once (include surrounding lines to make it unique). "
        "Prefer this over write_file for changing existing files — it can't clobber "
        "the rest of the file."
    ),
    parameters={
        "path": {"type": "string", "description": "relative file path in workspace"},
        "old": {"type": "string", "description": "exact text to replace (must be unique)"},
        "new": {"type": "string", "description": "replacement text"},
    },
)
def edit_file(path: str, old: str, new: str) -> str:
    p = _safe(path)
    if not p.exists():
        return f"ERROR: no such file: {path}"
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n == 0:
        return f"ERROR: `old` not found in {path}. Read the file first."
    if n > 1:
        return f"ERROR: `old` appears {n} times — make it unique (add context lines)."
    p.write_text(text.replace(old, new), encoding="utf-8")
    return f"edited {path}: 1 replacement"


@tool(
    description="Search file CONTENTS for a regex. Returns matching lines as path:line:text.",
    parameters={
        "pattern": {"type": "string", "description": "Python regex to search for"},
        "glob": {"type": "string", "description": "file glob to limit search, e.g. '*.py' (default all)"},
    },
)
def grep(pattern: str, glob: str = "*") -> str:
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return f"ERROR: bad regex: {e}"
    hits = []
    for f in sorted(WORKSPACE.rglob(glob)):
        if not f.is_file():
            continue
        try:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    rel = f.relative_to(WORKSPACE)
                    hits.append(f"{rel}:{i}:{line.strip()[:200]}")
                    if len(hits) >= 100:
                        return "\n".join(hits) + "\n... (truncated at 100)"
        except (OSError, UnicodeError):
            continue
    return "\n".join(hits) or "(no matches)"


@tool(
    description="Find files by name pattern (glob), e.g. '**/*.py'. Returns relative paths.",
    parameters={"pattern": {"type": "string", "description": "glob pattern, e.g. '**/*.py'"}},
)
def glob_files(pattern: str) -> str:
    out = [str(p.relative_to(WORKSPACE)) for p in sorted(WORKSPACE.glob(pattern)) if p.is_file()]
    return "\n".join(out[:200]) or "(no files)"


@tool(
    description=(
        "Run a Python snippet with the working directory set to a workspace subfolder, "
        "so you can `import` and TEST the files in a multi-file project there. Use this "
        "to verify your edits to a project actually work (run_python can't see project files)."
    ),
    parameters={
        "dir": {"type": "string", "description": "project folder in workspace, e.g. 'repo-002'"},
        "code": {"type": "string", "description": "Python to run (e.g. import and assert)"},
        "timeout_s": {"type": "integer", "description": "max seconds (default 15)"},
    },
)
def run_in_project(dir: str, code: str, timeout_s: int = 15) -> str:
    import subprocess
    import sys
    base = _safe(dir)
    if not base.is_dir():
        return f"ERROR: not a directory in workspace: {dir}"
    try:
        proc = subprocess.run([sys.executable, "-B", "-c", code], cwd=str(base),
                              capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return f"ERROR: timed out after {timeout_s}s"
    out = (proc.stdout or "")[-3000:]
    err = (proc.stderr or "")[-1500:]
    res = f"exit={proc.returncode}\n--- stdout ---\n{out}"
    if err.strip():
        res += f"\n--- stderr ---\n{err}"
    return res
