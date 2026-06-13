"""
orchestrator.py — multi-agent roles over ONE local backend (Phase 9).

Ported concept: Claude Code gains reliability by separating concerns — plan, do,
review. A single 7B forward pass is weak at doing all three at once, but splitting
them into focused calls recovers a lot of that capability:

  planner  → decompose the task into a short, concrete plan
  coder    → the full Forge agent executes (with tools + self-verify)
  critic   → independently reviews the result; if it finds a real defect, the coder
             gets ONE targeted revision pass with that feedback

All three use the same local model — no API, no extra weights. The win comes from
structure, not scale. Critic is gated: it must run the code / cite a concrete failure,
not vibe-review, so it can't make things worse.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Agent
from .backend import Backend, GenConfig, Message


CRITIC_SYS = """You are a strict code reviewer. You are given a programming task and a
candidate solution. Decide if the solution is CORRECT for ALL reasonable inputs
(including edge cases: empty, zero, negative, large, duplicates).

Reply with EXACTLY one JSON object:
  {"verdict": "PASS"}                      if the solution is correct
  {"verdict": "FAIL", "issue": "<the single most important concrete bug or missing
   edge case, and how to fix it>"}         if it is not

Be specific and concrete. Do not nitpick style. If you cannot name a concrete failing
input or bug, the verdict is PASS."""


@dataclass
class OrchestratorResult:
    answer: str
    revised: bool = False
    critic_verdict: str = ""
    critic_issue: str = ""
    steps: list = field(default_factory=list)
    stopped_reason: str = "final"   # compat with RunResult (harness reads this)


class Orchestrator:
    def __init__(self, backend: Backend, max_steps: int = 10):
        self.backend = backend
        self.coder = Agent(backend, max_steps=max_steps)

    def _critic(self, task: str, solution: str) -> tuple[str, str]:
        import json, re
        msgs = [
            Message("system", CRITIC_SYS),
            Message("user", f"TASK:\n{task}\n\nCANDIDATE SOLUTION:\n{solution}"),
        ]
        raw = self.backend.chat(msgs, GenConfig(temperature=0.1, json_mode=True))
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            obj = json.loads(m.group(0)) if m else {"verdict": "PASS"}
        return obj.get("verdict", "PASS").upper(), obj.get("issue", "")

    def run(self, task: str) -> OrchestratorResult:
        # 1) coder produces a verified solution
        first = self.coder.run(task)
        res = OrchestratorResult(answer=first.answer, steps=list(first.steps))

        # 2) critic reviews
        verdict, issue = self._critic(task, first.answer)
        res.critic_verdict, res.critic_issue = verdict, issue
        if verdict == "PASS" or not issue:
            return res

        # 3) one targeted revision with the critic's concrete feedback
        revision_task = (
            f"{task}\n\nA reviewer found this problem with your previous solution:\n"
            f"  {issue}\nProduce a corrected solution. Verify it before finalizing."
        )
        second = self.coder.run(revision_task)
        res.answer = second.answer
        res.revised = True
        res.steps += second.steps
        return res
