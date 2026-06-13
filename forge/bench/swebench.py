"""
swebench.py — run Forge on real SWE-bench issues, produce predictions (Phase 15++).

SWE-bench is the real test of "great at coding": fix an actual GitHub issue in a real
repo (django, flask, sympy, ...) so its hidden tests pass. This is where harness, tools,
and memory matter most — a single-shot model can't navigate a real codebase.

Clean division of labor (the honest way to do this):
  - THIS file = generation: clone the repo at the bug commit, give Forge the issue +
    the repo in its workspace, let it explore/edit/verify, then capture `git diff` as the
    model's patch. Writes predictions.jsonl in official SWE-bench format.
  - SCORING = the official harness (handles Docker, deps, the real test suite):
        pip install swebench
        python -m swebench.harness.run_evaluation \\
          --predictions_path predictions.jsonl \\
          --dataset_name princeton-nlp/SWE-bench_Lite --run_id forge1
    Don't reinvent that — it's battle-tested and env-correct.

Run (on a box with git + the repos' build deps; ideally the rented GPU box):
    pip install datasets
    python -m bench.swebench --limit 5
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.agent import Agent          # noqa: E402
from forge.backend import get_backend  # noqa: E402
from forge.tools import files as _files  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"

PROMPT = """You are fixing a real bug in a Python project checked out in the folder
`{slug}/` in your workspace.

ISSUE:
{problem}

Use glob_files/grep/read_file to find the relevant code in `{slug}/`, make the SMALLEST
correct fix with edit_file, and verify with run_in_project. Change only source files
needed to resolve the issue. Do not edit tests."""


def load_instances(limit: int, split: str = "test") -> list[dict]:
    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split=split)
    return [ds[i] for i in range(min(limit, len(ds)))]


def _sh(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)


def solve_instance(agent: Agent, inst: dict, work: Path) -> str:
    """Clone repo@base_commit into the workspace, let Forge edit, return git diff."""
    slug = inst["repo"].split("/")[-1]
    repo_dir = work / slug
    if repo_dir.exists():
        import shutil
        shutil.rmtree(repo_dir, ignore_errors=True)
    url = f"https://github.com/{inst['repo']}.git"
    _sh(["git", "clone", "--quiet", url, str(repo_dir)], cwd=str(work))
    _sh(["git", "checkout", "--quiet", inst["base_commit"]], cwd=str(repo_dir))
    _sh(["git", "config", "user.email", "f@f"], cwd=str(repo_dir))
    _sh(["git", "config", "user.name", "forge"], cwd=str(repo_dir))

    agent.run(PROMPT.format(slug=slug, problem=inst["problem_statement"][:4000]))

    diff = _sh(["git", "diff"], cwd=str(repo_dir))
    return diff.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default="predictions.jsonl")
    ap.add_argument("--max-steps", type=int, default=20)
    a = ap.parse_args()

    agent = Agent(get_backend(a.model), max_steps=a.max_steps)
    model_name = agent.backend.name
    work = _files.WORKSPACE
    insts = load_instances(a.limit)
    print(f"Generating patches for {len(insts)} SWE-bench Lite instances...\n")

    preds = []
    t0 = time.time()
    for i, inst in enumerate(insts, 1):
        ts = time.time()
        try:
            patch = solve_instance(agent, inst, work)
        except Exception as e:
            patch = ""
            print(f"  [{i}] {inst['instance_id']}  ERROR {type(e).__name__}: {e}")
        nonempty = bool(patch.strip())
        preds.append({"instance_id": inst["instance_id"],
                      "model_name_or_path": model_name, "model_patch": patch})
        print(f"  [{i}] {inst['instance_id']:<28} "
              f"{'patch' if nonempty else 'EMPTY':<6} {time.time()-ts:5.0f}s")

    out = Path(a.out)
    out.write_text("\n".join(json.dumps(p) for p in preds), encoding="utf-8")
    n_patched = sum(1 for p in preds if p["model_patch"].strip())
    print(f"\nWrote {len(preds)} predictions ({n_patched} non-empty) -> {out}  "
          f"({time.time()-t0:.0f}s)")
    print("\nScore them with the OFFICIAL harness (handles Docker + real tests):")
    print("  pip install swebench")
    print(f"  python -m swebench.harness.run_evaluation --predictions_path {out} \\")
    print("    --dataset_name princeton-nlp/SWE-bench_Lite --run_id forge1 --max_workers 4")


if __name__ == "__main__":
    main()
