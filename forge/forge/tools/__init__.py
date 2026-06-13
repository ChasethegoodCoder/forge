"""
Tool registry. A "tool" is a Python callable + a JSON schema describing it to
the model. The agent reads the registry, shows the model what's available, and
dispatches the model's chosen call back to the function.

Why a registry instead of hardcoding: capability grows by *adding tools*, not by
rewriting the agent. This is the cheapest, highest-leverage way to close the gap
to Sonnet 4.6 early on — Claude Code is powerful largely because of its tools.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]   # JSON-schema-ish: {arg: {type, description}}
    func: Callable[..., str]
    dangerous: bool = False      # if True, agent asks before running

    def spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


REGISTRY: dict[str, Tool] = {}


def tool(description: str, parameters: dict[str, Any], dangerous: bool = False):
    """Decorator to register a function as a tool."""
    def wrap(fn: Callable[..., str]) -> Callable[..., str]:
        REGISTRY[fn.__name__] = Tool(
            name=fn.__name__,
            description=description,
            parameters=parameters,
            func=fn,
            dangerous=dangerous,
        )
        return fn
    return wrap


def load_all() -> dict[str, Tool]:
    """Import tool modules so their decorators register. Returns the registry."""
    from . import files, shell, python_exec, code, planning  # noqa: F401
    return REGISTRY


def specs() -> list[dict[str, Any]]:
    return [t.spec() for t in REGISTRY.values()]


def call(name: str, args: dict[str, Any]) -> str:
    if name not in REGISTRY:
        return f"ERROR: unknown tool '{name}'. Available: {list(REGISTRY)}"
    fn = REGISTRY[name].func
    # only pass args the function actually accepts
    sig = inspect.signature(fn)
    clean = {k: v for k, v in args.items() if k in sig.parameters}
    try:
        return str(fn(**clean))
    except Exception as e:  # tools must never crash the agent loop
        return f"ERROR running {name}: {type(e).__name__}: {e}"
