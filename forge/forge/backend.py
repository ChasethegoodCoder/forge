"""
backend.py — the reasoning engine interface.

Design decision: everything in Forge talks to the model through ONE small
interface (`Backend`). Today the only implementation is Ollama (local, free,
runs on your RTX 4070). Tomorrow, if you ever fine-tune your own checkpoint and
serve it, you implement the same 3 methods and nothing else in the codebase
changes. This is the "swappable brain" principle — the harness is the durable
asset; the weights behind it are replaceable.

No API keys. No cloud. Fully local.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator

import requests


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    # for tool results we keep the name so the model knows which call this answers
    name: str | None = None


@dataclass
class GenConfig:
    temperature: float = 0.2
    top_p: float = 0.9
    num_ctx: int = 8192          # context window; raise if your model + VRAM allow
    max_tokens: int = 2048
    stop: list[str] = field(default_factory=list)
    json_mode: bool = False      # force valid-JSON output (fixes escaping/parsing)


class Backend:
    """Abstract engine. Implement these and the whole agent works on a new model."""

    name: str = "abstract"

    def chat(self, messages: list[Message], cfg: GenConfig) -> str:
        raise NotImplementedError

    def stream(self, messages: list[Message], cfg: GenConfig) -> Iterator[str]:
        # default: non-streaming fallback
        yield self.chat(messages, cfg)


class OllamaBackend(Backend):
    """Local model served by Ollama (http://localhost:11434)."""

    def __init__(self, model: str = "qwen2.5:7b-instruct",
                 host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")
        self.name = f"ollama:{model}"

    def _payload(self, messages: list[Message], cfg: GenConfig, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": stream,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "options": {
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "num_ctx": cfg.num_ctx,
                "num_predict": cfg.max_tokens,
                "stop": cfg.stop or None,
            },
        }
        if cfg.json_mode:
            payload["format"] = "json"
        return payload

    def chat(self, messages: list[Message], cfg: GenConfig) -> str:
        r = requests.post(
            f"{self.host}/api/chat",
            json=self._payload(messages, cfg, stream=False),
            timeout=600,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def stream(self, messages: list[Message], cfg: GenConfig) -> Iterator[str]:
        with requests.post(
            f"{self.host}/api/chat",
            json=self._payload(messages, cfg, stream=True),
            stream=True,
            timeout=600,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if chunk.get("done"):
                    break
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    yield piece


def get_backend(model: str | None = None) -> Backend:
    """Factory. Reads config later; for now returns local Ollama."""
    return OllamaBackend(model=model or "qwen2.5:7b-instruct")
