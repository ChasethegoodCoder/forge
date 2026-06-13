"""
agent.py — the ReAct-style reasoning/acting loop. This is Forge's core IP.

The loop: the model is told its tools and a strict output protocol. Each turn it
emits ONE JSON action — either call a tool or give the final answer. We run the
tool, feed the result back as an observation, and iterate until it finalizes or
hits the step budget. This "think → act → observe" cycle is exactly how Claude
Code operates; replicating it well is how a 7B model punches above its weight.

Protocol (model must emit a single JSON object):
    {"thought": "...", "tool": "run_python", "args": {"code": "..."}}
  or
    {"thought": "...", "final": "the answer for the user"}
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .backend import Backend, GenConfig, Message
from . import tools as toolkit


SYSTEM_TEMPLATE = """You are Forge, an autonomous CODING agent. Your top priority is producing
code that is CORRECT and actually runs. You solve tasks by reasoning step by step
and using tools. On EVERY turn you reply with EXACTLY ONE JSON object and nothing
else — no prose outside the JSON.

Two valid shapes:
  {{"thought": "<brief reasoning>", "tool": "<tool_name>", "args": {{...}}}}
  {{"thought": "<brief reasoning>", "final": "<answer for the user>"}}

Rules (coding-first):
- For ANY coding task: write the function, then ALWAYS call run_python to execute it
  against a few example inputs and confirm it works BEFORE you finalize. Never finalize
  unverified code.
- If a test reveals a bug, fix it and re-run until it passes.
- Put the final code in a ```python code block in the "final" field.
- For math/logic, verify the answer with run_python too.
- One tool per turn. Read each observation before the next action.

Available tools:
{tool_docs}
"""


@dataclass
class Step:
    thought: str
    action: str            # tool name or "final"
    args: dict
    observation: str = ""


@dataclass
class RunResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    stopped_reason: str = "final"   # "final" | "budget" | "error"


def _tool_docs() -> str:
    lines = []
    for s in toolkit.specs():
        params = ", ".join(f"{k}:{v.get('type','any')}" for k, v in s["parameters"].items())
        lines.append(f"- {s['name']}({params}): {s['description']}")
    return "\n".join(lines)


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_action(text: str) -> dict:
    """Extract the JSON action. Local models sometimes wrap it in prose/fences,
    or emit a bare value. Guarantee a dict so the loop never crashes."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).rstrip("`").strip()
    for candidate in (text, (_JSON_RE.search(text).group(0) if _JSON_RE.search(text) else None)):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    # bare value or unparseable output → treat as the final answer
    return {"final": text}


class Agent:
    def __init__(self, backend: Backend, max_steps: int = 8,
                 cfg: GenConfig | None = None, auto_approve: bool = True,
                 self_verify: bool = True):
        self.backend = backend
        self.max_steps = max_steps
        # low temp: deterministic code; json_mode: force valid, properly-escaped actions
        self.cfg = cfg or GenConfig(temperature=0.1, json_mode=True)
        self.auto_approve = auto_approve
        self.self_verify = self_verify
        toolkit.load_all()

    def run(self, task: str, system_extra: str = "") -> RunResult:
        system = SYSTEM_TEMPLATE.format(tool_docs=_tool_docs())
        if system_extra:
            system += "\n\n" + system_extra
        msgs = [Message("system", system), Message("user", task)]
        result = RunResult(answer="")
        ran_code = False      # has the agent executed code this run?
        nudged = False        # have we already pushed back once on unverified code?

        for _ in range(self.max_steps):
            raw = self.backend.chat(msgs, self.cfg)
            action = _parse_action(raw)

            if "final" in action:
                answer = str(action["final"])
                looks_like_code = bool(re.search(r"```|def |class |import ", answer))
                # Self-verification gate: don't accept code that was never run.
                if self.self_verify and looks_like_code and not ran_code and not nudged:
                    nudged = True
                    msgs.append(Message("assistant", json.dumps(action)))
                    msgs.append(Message(
                        "tool",
                        "VERIFICATION REQUIRED: you have not run this code yet. Call "
                        "run_python to execute it against example inputs and confirm it "
                        "works, then finalize. Do not finalize unverified code.",
                        name="verifier",
                    ))
                    result.steps.append(Step(action.get("thought", ""), "verify_nudge", {}, "blocked unverified code"))
                    continue
                result.answer = answer
                result.stopped_reason = "final"
                result.steps.append(Step(action.get("thought", ""), "final", {}, ""))
                return result

            name = action.get("tool", "")
            args = action.get("args", {}) or {}
            thought = action.get("thought", "")

            tool = toolkit.REGISTRY.get(name)
            if tool and tool.dangerous and not self.auto_approve:
                obs = f"BLOCKED: tool '{name}' is dangerous and not approved."
            else:
                obs = toolkit.call(name, args)
            if name == "run_python":
                ran_code = True

            result.steps.append(Step(thought, name, args, obs))
            # feed the action + observation back so the model can continue
            msgs.append(Message("assistant", json.dumps(action)))
            msgs.append(Message("tool", f"observation from {name}:\n{obs}", name=name))

        result.stopped_reason = "budget"
        result.answer = result.steps[-1].observation if result.steps else ""
        return result
