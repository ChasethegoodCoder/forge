"""
builder.py — incremental project builder (work like a frontier model, at 7B scale).

A 7B can't one-shot a whole program (too much to hold at once) — but it CAN do one
small piece at a time. This decomposes a big task into a sequence of small files/steps,
then builds each one into the project folder and verifies it before moving on, the way
I (a frontier model) naturally plan → implement → check → continue.

It won't match a big model's quality, but it turns "useless stub" into "actually built,
piece by piece." Knowing its own limits — small steps, verify each — is the whole trick.

    from forge.builder import ProjectBuilder
    ProjectBuilder(get_backend()).build("a tic-tac-toe game you play in the terminal")
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .agent import Agent
from .backend import Backend, GenConfig, Message
from .tools.files import WORKSPACE

PLAN_SYS = """You are a senior engineer planning a SMALL Python project for a junior dev who
can only handle one little file at a time. Break the task into 2-6 ordered steps, each a
single file with a clear, narrow job. Keep it realistic and minimal — no over-engineering.

Reply with ONLY a JSON object:
{"entry": "<file to run, e.g. main.py>",
 "steps": [{"file": "<name.py>", "what": "<what this file should contain, concretely>"}, ...]}
Order steps so each only depends on earlier ones. The LAST step MUST create the `entry`
file — a small main that imports the others and runs the program. The entry file must be
one of the steps."""


@dataclass
class BuildResult:
    project_dir: str
    entry: str
    steps: list = field(default_factory=list)   # [{file, ok, note}]


class ProjectBuilder:
    def __init__(self, backend: Backend, on_progress=None):
        self.backend = backend
        self.agent = Agent(backend, max_steps=12)
        self.on_progress = on_progress or (lambda m: print(m, flush=True))

    def plan(self, task: str) -> dict:
        raw = self.backend.chat(
            [Message("system", PLAN_SYS), Message("user", task)],
            GenConfig(temperature=0.2, json_mode=True, max_tokens=700))
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            return json.loads(m.group(0)) if m else {"entry": "main.py", "steps": []}

    def build(self, task: str, project_dir: str = "project") -> BuildResult:
        plan = self.plan(task)
        steps = plan.get("steps", [])
        entry = plan.get("entry", "main.py")
        res = BuildResult(project_dir=project_dir, entry=entry)

        self.on_progress(f"\nPlan: {len(steps)} steps -> {project_dir}/ (run: {entry})")
        for i, step in enumerate(steps, 1):
            fname, what = step.get("file", f"step{i}.py"), step.get("what", "")
            self.on_progress(f"[{i}/{len(steps)}] {fname} — {what[:60]}")
            prompt = (
                f"You are building a project incrementally in the workspace folder "
                f"`{project_dir}/`. Overall goal: {task}\n\n"
                f"Files already created live in `{project_dir}/` — use glob_files/read_file "
                f"to see what's there and reuse it.\n\n"
                f"NOW do ONLY this step: write `{project_dir}/{fname}` so that it: {what}\n"
                f"Use write_file to create it, then run_in_project('{project_dir}', ...) to "
                f"verify it imports/works with the other files. Keep it small and correct.")
            self.agent.run(prompt)
            path = WORKSPACE / project_dir / fname
            ok = path.exists()
            res.steps.append({"file": fname, "ok": ok,
                              "note": "created" if ok else "MISSING"})
            self.on_progress(f"      {'ok' if ok else 'FAILED'}")

        # Make sure there's a runnable entry. If the planned entry wasn't created,
        # fall back to a built file that has a __main__ block, then add a main step.
        proj = WORKSPACE / project_dir
        if not (proj / entry).exists():
            runnable = next((s["file"] for s in res.steps if s["ok"]
                             and "__main__" in (proj / s["file"]).read_text(encoding="utf-8", errors="ignore")),
                            None)
            if runnable:
                entry = runnable
            else:
                self.on_progress(f"[+] no entry yet — wiring a main that runs the project")
                self.agent.run(
                    f"In the workspace folder `{project_dir}/`, create `{project_dir}/{entry}`: "
                    f"a small script that imports the other files there and runs the program "
                    f"({task}). Read the existing files first, then write_file and verify with "
                    f"run_in_project('{project_dir}', ...).")
            res.entry = entry

        done = sum(1 for s in res.steps if s["ok"])
        self.on_progress(f"\nBuilt {done}/{len(steps)} files in {proj}")
        self.on_progress(f"Run it:  cd {proj} && python {res.entry}")
        return res
