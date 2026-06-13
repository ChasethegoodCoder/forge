"""
store.py — GoldStore: the accumulating set of VERIFIED training examples (P14
"store best only" + P7 dataset factory output).

Discipline: nothing enters the store unless it passed its own tests. Each example
carries the schema from your Phase 7 spec (instruction, answer, reasoning, difficulty,
category, quality). Dedup by content hash so the flywheel doesn't pile up duplicates.
This store is the fuel for fine-tuning (P8) and for expanding the benchmark.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

GOLD_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "gold" / "examples.jsonl"


@dataclass
class Example:
    instruction: str
    answer: str                 # the verified solution (code)
    tests: str = ""             # tests it passed (provenance of "verified")
    reasoning: str = ""         # short reasoning summary
    category: str = "coding"
    difficulty: int = 2         # 1..5
    quality: float = 0.0        # 0..1 quality score (see filter.py)
    source: str = "factory"     # factory | benchmark | human
    verified: bool = True
    ts: float = field(default_factory=time.time)

    def key(self) -> str:
        return hashlib.sha256((self.instruction.strip() + "||" + self.answer.strip())
                              .encode("utf-8")).hexdigest()[:16]


class GoldStore:
    def __init__(self, path: Path = GOLD_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._keys: set[str] = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self._keys.add(json.loads(line)["key"])
                    except (json.JSONDecodeError, KeyError):
                        pass

    def add(self, ex: Example) -> bool:
        """Append if new and verified. Returns True if stored."""
        if not ex.verified:
            return False
        k = ex.key()
        if k in self._keys:
            return False
        rec = asdict(ex)
        rec["key"] = k
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        self._keys.add(k)
        return True

    def all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def __len__(self) -> int:
        return len(self._keys)
