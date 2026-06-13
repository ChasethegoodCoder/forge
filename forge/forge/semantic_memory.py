"""
semantic_memory.py — recall by MEANING, not exact key (Phase 5 / P5).

Upgrades the v0 JSON key/value memory to vector search, but stays fully local and
dependency-light: embeddings come from Ollama (`nomic-embed-text`), similarity is
pure-Python cosine. No torch, no chromadb. Same spirit as memory.py — a store you
can open and read.

Why it matters: lets the agent retrieve relevant past facts/solutions across a long
task or many sessions by semantic similarity, instead of needing the exact key. This
is a core piece of the Claude-Code-style harness (project memory).
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from .backend import OllamaBackend

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "memory" / "vectors.json"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class SemanticMemory:
    def __init__(self, backend: OllamaBackend | None = None, path: Path = DEFAULT_PATH,
                 embed_model: str = "nomic-embed-text"):
        self.backend = backend or OllamaBackend()
        self.embed_model = embed_model
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[dict] = []
        if self.path.exists():
            try:
                self._items = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._items), encoding="utf-8")

    def add(self, text: str, **meta) -> None:
        vec = self.backend.embed(text, self.embed_model)
        self._items.append({"text": text, "vec": vec, "t": time.time(), "meta": meta})
        self._save()

    def search(self, query: str, k: int = 3, min_score: float = 0.3) -> list[dict]:
        """Return up to k most semantically-similar items above min_score."""
        if not self._items:
            return []
        qv = self.backend.embed(query, self.embed_model)
        scored = [(_cosine(qv, it["vec"]), it) for it in self._items]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"text": it["text"], "score": round(s, 3), "meta": it["meta"]}
                for s, it in scored[:k] if s >= min_score]

    def __len__(self) -> int:
        return len(self._items)
