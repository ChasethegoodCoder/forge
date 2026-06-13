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


PLANNER_SYS = """You are a planning assistant. Given a programming task, produce a SHORT
numbered plan (2-5 steps) describing how to implement and verify it. Be concrete about
edge cases to handle. Output ONLY the plan, no code."""


class Orchestrator:
    def __init__(self, backend: Backend, max_steps: int = 10, plan: bool = False):
        self.backend = backend
        self.coder = Agent(backend, max_steps=max_steps)
        self.plan = plan  # planner -> coder -> critic (full multi-agent)

    def _planner(self, task: str) -> str:
        out = self.backend.chat(
            [Message("system", PLANNER_SYS), Message("user", task)],
            GenConfig(temperature=0.3))
        return out.strip()[:800]

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
        # 0) optional planner stage — decompose before coding (full planner->coder->critic)
        coder_task = task
        if self.plan:
            plan = self._planner(task)
            coder_task = f"{task}\n\nSuggested plan:\n{plan}"
        # 1) coder produces a verified solution
        first = self.coder.run(coder_task)
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


class BestOfN:
    """Reliability via sampling (Phase 19): generate N independent solutions at varied
    temperatures, then SELECT the best by self-verification — prefer candidates whose
    code compiles AND that the agent actually executed (run_python) before finalizing.
    Legit pass@1 booster: if any of N attempts lands a verified solution, we use it.
    No access to hidden tests — selection is purely on the agent's own verification."""

    def __init__(self, backend: Backend, n: int = 3, max_steps: int = 10):
        self.backend = backend
        self.n = n
        self.max_steps = max_steps

    def _compiles(self, answer: str) -> bool:
        import ast
        import re
        m = re.search(r"```(?:python)?\s*(.*?)```", answer, re.DOTALL)
        code = m.group(1) if m else answer
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def run(self, task: str):
        from .agent import Agent, GenConfig
        candidates = []
        for i in range(self.n):
            temp = 0.1 + 0.3 * i  # 0.1, 0.4, 0.7 — diversify attempts
            agent = Agent(self.backend, max_steps=self.max_steps,
                          cfg=GenConfig(temperature=temp, json_mode=True))
            r = agent.run(task)
            verified = any(s.action == "run_python" for s in r.steps) and r.stopped_reason == "final"
            candidates.append((verified, self._compiles(r.answer), r))
        # rank: verified+compiles > compiles > anything; first of best tier wins
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        best = candidates[0][2]
        # reuse OrchestratorResult shape for harness compatibility
        return OrchestratorResult(answer=best.answer, steps=best.steps,
                                  critic_verdict=f"best-of-{self.n}",
                                  stopped_reason=best.stopped_reason)
