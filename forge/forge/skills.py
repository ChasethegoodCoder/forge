"""
skills.py — reusable scaffolds the builder starts from (Phase C).

A 7B fails at blank-page problems but is fine FILLING IN a correct skeleton. A "skill"
is exactly that: a tested starter (working pygame loop, flask app, CLI, ...) plus notes.
When a build task matches a skill's triggers, the builder drops the scaffold into the
project and the model only has to fill the gaps — hiding the parts it can't invent.
This is the biggest free quality lever for a small model: don't make it start from zero.

A skill lives in  skills/<name>/  with:
    skill.json   -> {"name", "triggers": ["regex", ...], "description", "scaffold": ["file.py", ...]}
    <scaffold files>
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


@dataclass
class Skill:
    name: str
    triggers: list[str]
    description: str
    scaffold: list[str]
    path: Path

    def matches(self, task: str) -> bool:
        return any(re.search(t, task, re.I) for t in self.triggers)

    def install(self, dest_dir: Path) -> list[str]:
        """Copy scaffold files into the project. Returns the filenames installed."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        done = []
        for f in self.scaffold:
            src = self.path / f
            if src.exists():
                shutil.copy(src, dest_dir / f)
                done.append(f)
        return done


def load_skills() -> list[Skill]:
    out = []
    if not SKILLS_DIR.exists():
        return out
    for d in sorted(SKILLS_DIR.iterdir()):
        meta = d / "skill.json"
        if meta.is_dir() or not meta.exists():
            continue
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            out.append(Skill(m["name"], m.get("triggers", []), m.get("description", ""),
                             m.get("scaffold", []), d))
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def best_match(task: str) -> Skill | None:
    for s in load_skills():
        if s.matches(task):
            return s
    return None
