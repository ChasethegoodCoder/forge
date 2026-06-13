"""File tools: read, write, list. Sandboxed to a working directory."""
from __future__ import annotations

import os
from pathlib import Path

from . import tool

# Agent file ops are confined under WORKSPACE for safety.
WORKSPACE = Path(os.environ.get("FORGE_WORKSPACE", Path.cwd() / "workspace")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)


def _safe(path: str) -> Path:
    p = (WORKSPACE / path).resolve()
    if not str(p).startswith(str(WORKSPACE)):
        raise ValueError(f"path escapes workspace: {path}")
    return p


@tool(
    description="Read a UTF-8 text file from the workspace. Returns its contents.",
    parameters={"path": {"type": "string", "description": "relative path in workspace"}},
)
def read_file(path: str) -> str:
    p = _safe(path)
    if not p.exists():
        return f"ERROR: no such file: {path}"
    return p.read_text(encoding="utf-8", errors="replace")


@tool(
    description="Write text to a file in the workspace, creating parent dirs. Overwrites.",
    parameters={
        "path": {"type": "string", "description": "relative path in workspace"},
        "content": {"type": "string", "description": "full file contents to write"},
    },
)
def write_file(path: str, content: str) -> str:
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {path}"


@tool(
    description="List files under a workspace directory (recursive, max 200).",
    parameters={"path": {"type": "string", "description": "relative dir, '.' for root"}},
)
def list_files(path: str = ".") -> str:
    base = _safe(path)
    if not base.exists():
        return f"ERROR: no such dir: {path}"
    out = []
    for p in sorted(base.rglob("*"))[:200]:
        out.append(str(p.relative_to(WORKSPACE)))
    return "\n".join(out) or "(empty)"
