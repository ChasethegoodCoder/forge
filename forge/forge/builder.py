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

    def _verify(self, project_dir: str, fname: str) -> tuple[bool, str]:
        """Import the file inside the project (deps resolve). Catches syntax/name/import
        errors without running game loops. Returns (ok, error_tail)."""
        import subprocess
        import sys
        proj = WORKSPACE / project_dir
        if not (proj / fname).exists():
            return False, f"{fname} was not created"
        module = fname[:-3] if fname.endswith(".py") else fname
        try:
            p = subprocess.run([sys.executable, "-B", "-c", f"import {module}"],
                               cwd=str(proj), capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return False, "import timed out"
        if p.returncode == 0:
            return True, ""
        err = (p.stderr or "").strip().splitlines()
        return False, "\n".join(err[-6:])

    @staticmethod
    def _env_missing(err: str, project_dir: str) -> str | None:
        """If the error is a missing THIRD-PARTY package (not a project file), return its
        name — it's an environment problem, not a code bug, so don't try to 'fix' it."""
        m = re.search(r"ModuleNotFoundError: No module named '([\w.]+)'", err or "")
        if not m:
            return None
        mod = m.group(1).split(".")[0]
        if (WORKSPACE / project_dir / f"{mod}.py").exists():
            return None  # it's a local module the agent forgot to create -> fixable
        return mod

    def _build_file(self, project_dir: str, fname: str, what: str, task: str,
                    max_fix: int = 2) -> bool:
        """Write the file, then verify-and-fix until it imports cleanly (mastery)."""
        self.agent.run(
            f"You are building a project incrementally in the workspace folder "
            f"`{project_dir}/`. Overall goal: {task}\n\n"
            f"Files already created live in `{project_dir}/` — use glob_files/read_file to "
            f"see them and reuse their classes/functions.\n\n"
            f"NOW do ONLY this step: write `{project_dir}/{fname}` so that it: {what}\n"
            f"write_file it, then run_in_project('{project_dir}', ...) to verify it imports "
            f"and works with the others. Keep it small and correct.")
        for _ in range(max_fix):
            ok, err = self._verify(project_dir, fname)
            if ok:
                return True
            pkg = self._env_missing(err, project_dir)
            if pkg:
                self.on_progress(f"        needs `pip install {pkg}` (env, not a code bug) "
                                 f"— skipping fix, code looks fine")
                return True  # code is fine; the machine just lacks the package
            self.on_progress(f"        fixing: {err.splitlines()[-1][:60] if err else 'error'}")
            self.agent.run(
                f"The file `{project_dir}/{fname}` fails to import:\n{err}\n\n"
                f"Fix it: read_file `{project_dir}/{fname}` (and any file it imports), find "
                f"the bug, edit_file to fix, and verify with run_in_project('{project_dir}', "
                f"'import {fname[:-3]}'). Only fix the error.")
        return self._verify(project_dir, fname)[0]

    def _build_on_scaffold(self, task: str, project_dir: str, skill) -> BuildResult:
        """Skill path: install a working scaffold, then have the model FILL IN the TODOs
        (the parts it can do) instead of inventing the whole thing (which it can't)."""
        proj = WORKSPACE / project_dir
        installed = skill.install(proj)
        entry = installed[0] if installed else "main.py"
        res = BuildResult(project_dir=project_dir, entry=entry)
        self.on_progress(f"\nSkill '{skill.name}' — starting from working scaffold: {installed}")
        self.on_progress(f"Filling in {entry} for: {task}")

        self.agent.run(
            f"There is a WORKING, runnable scaffold at `{project_dir}/{entry}` with TODO "
            f"comments marking what to add. Goal: {task}\n\n"
            f"Steps: read_file `{project_dir}/{entry}` to understand the structure, then use "
            f"edit_file to implement EACH TODO (spawn/move/draw obstacles, collision that "
            f"sets self.dead, scoring/restart). KEEP the existing working loop and physics. "
            f"After each edit verify it still imports with run_in_project('{project_dir}', "
            f"'import {entry[:-3]}'). Do not rewrite from scratch.")

        ok = self._build_file_verify_fix(project_dir, entry, max_fix=2)
        res.steps.append({"file": entry, "ok": ok, "note": "scaffold filled"})
        status = "runs (or needs a pip install)" if ok else "has errors"
        self.on_progress(f"\nBuilt {project_dir}/{entry} — {status}")
        self.on_progress(f"Run it:  cd {proj} && python {entry}")
        return res

    def _build_file_verify_fix(self, project_dir: str, fname: str, max_fix: int = 2) -> bool:
        for _ in range(max_fix):
            ok, err = self._verify(project_dir, fname)
            if ok:
                return True
            if self._env_missing(err, project_dir):
                return True
            self.on_progress(f"        fixing: {err.splitlines()[-1][:60] if err else 'error'}")
            self.agent.run(
                f"`{project_dir}/{fname}` fails to import:\n{err}\nFix ONLY this error: "
                f"read_file it, edit_file the fix, verify with run_in_project('{project_dir}', "
                f"'import {fname[:-3]}').")
        return self._verify(project_dir, fname)[0]

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
        # Phase C: if a skill matches, start from its WORKING scaffold instead of blank.
        from .skills import best_match
        skill = best_match(task)
        if skill:
            return self._build_on_scaffold(task, project_dir, skill)

        plan = self.plan(task)
        steps = plan.get("steps", [])
        entry = plan.get("entry", "main.py")
        res = BuildResult(project_dir=project_dir, entry=entry)

        self.on_progress(f"\nPlan: {len(steps)} steps -> {project_dir}/ (run: {entry})")
        for i, step in enumerate(steps, 1):
            fname, what = step.get("file", f"step{i}.py"), step.get("what", "")
            self.on_progress(f"[{i}/{len(steps)}] {fname} — {what[:60]}")
            ok = self._build_file(project_dir, fname, what, task, max_fix=2)
            res.steps.append({"file": fname, "ok": ok,
                              "note": "works" if ok else "has errors"})
            self.on_progress(f"      {'ok' if ok else 'still broken after fixes'}")

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

        # integration pass: the whole program must import/wire together via the entry
        iok, ierr = self._verify(project_dir, res.entry)
        if not iok and (proj / res.entry).exists():
            self.on_progress(f"[integration] fixing: {ierr.splitlines()[-1][:60] if ierr else ''}")
            self.agent.run(
                f"The program's entry file `{project_dir}/{res.entry}` fails when the project "
                f"is run together:\n{ierr}\n\nFix the integration: read the relevant files in "
                f"`{project_dir}/`, correct the mismatch (wrong import, wrong function name, "
                f"bad call), edit_file, and verify with run_in_project('{project_dir}', "
                f"'import {res.entry[:-3]}'). ")
            iok = self._verify(project_dir, res.entry)[0]

        done = sum(1 for s in res.steps if s["ok"])
        status = "runs" if iok else "builds but has integration errors"
        self.on_progress(f"\nBuilt {done}/{len(steps)} files in {proj} — {status}")
        self.on_progress(f"Run it:  cd {proj} && python {res.entry}")
        return res
