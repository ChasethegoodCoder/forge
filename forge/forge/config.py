"""
config.py — single source of runtime settings (Phase 20).

Fixes the flagged bug: `config/forge.yaml` existed but nothing read it. Now the
backend and agent take their defaults from here. Degrades gracefully to built-in
defaults if the file or pyyaml is missing, so the system always runs.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "forge.yaml"

DEFAULTS: dict[str, Any] = {
    "engine": {
        "backend": "ollama",
        "model": "qwen2.5:7b-instruct",
        "host": "http://localhost:11434",
        "temperature": 0.1,
        "num_ctx": 8192,
    },
    "agent": {"max_steps": 8, "auto_approve_dangerous": False},
    "bench": {"suites": ["reasoning", "coding"], "max_steps": 8},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


_cache: dict[str, Any] | None = None


def load() -> dict[str, Any]:
    """Load merged config (cached). Built-in defaults <- forge.yaml overrides."""
    global _cache
    if _cache is not None:
        return _cache
    cfg = DEFAULTS
    try:
        import yaml
        if CONFIG_PATH.exists():
            cfg = _deep_merge(DEFAULTS, yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {})
    except Exception:
        pass  # any failure -> safe defaults

    # Env overrides — the easy way to point at a RENTED GPU without editing files:
    #   FORGE_HOST=http://<rented-box>:11434  FORGE_MODEL=llama3.1:70b
    import os
    if os.environ.get("FORGE_HOST"):
        cfg = _deep_merge(cfg, {"engine": {"host": os.environ["FORGE_HOST"]}})
    if os.environ.get("FORGE_MODEL"):
        cfg = _deep_merge(cfg, {"engine": {"model": os.environ["FORGE_MODEL"]}})
    _cache = cfg
    return cfg


def get(path: str, default: Any = None) -> Any:
    """Dotted lookup, e.g. get('engine.model')."""
    node: Any = load()
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node
