"""
memory.py — persistent memory, v0 (JSON-backed key/value + append log).

Start simple and honest: a JSON store you can inspect by eye. Phase 3 of the
roadmap upgrades this to semantic memory (embeddings + vector search) so the
agent can recall by meaning, not exact key. We keep the SAME interface here so
that upgrade swaps the backend without touching callers — same principle as the
model backend.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "memory" / "store.json"


class Memory:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {"facts": {}, "log": []}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def remember(self, key: str, value: str) -> None:
        self._data["facts"][key] = value
        self._save()

    def recall(self, key: str) -> str | None:
        return self._data["facts"].get(key)

    def all_facts(self) -> dict[str, str]:
        return dict(self._data["facts"])

    def log(self, event: str, **meta) -> None:
        self._data["log"].append({"t": time.time(), "event": event, **meta})
        self._save()
