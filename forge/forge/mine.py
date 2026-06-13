"""
mine.py — turn FAILURES into training data (Phase 8/9 self-improvement flywheel).

The most valuable training examples are the ones the model currently gets WRONG. This
miner:
  1. runs the benchmark tasks with the plain agent,
  2. for each FAILURE, retries with the stronger critic orchestrator (and best-of-N),
  3. if the stronger solver now PASSES the hidden test, that (task, verified-solution)
     pair is exactly a hard example the base model needs — store it in the GoldStore.

So the model's own weak spots become its curriculum. Fine-tuning on mined failures is
far more efficient than random generation, because every example targets a real gap.

  python -m forge.mine --suites coding agent
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bench.harness import load_suite          # noqa: E402
from bench.judge import score_one, clean_source, _extract_code  # noqa: E402
from forge.agent import Agent                  # noqa: E402
from forge.orchestrator import Orchestrator, BestOfN  # noqa: E402
from forge.backend import get_backend          # noqa: E402
from forge.factory.store import Example, GoldStore  # noqa: E402
from forge.factory.filter import quality, estimate_difficulty  # noqa: E402


def _passed(res, spec) -> tuple[bool, str]:
    executed = [s.args.get("code", "") for s in res.steps
                if s.action == "run_python" and isinstance(s.args, dict)]
    sc, _ = score_one(res.answer, spec, extra_code=executed)
    if sc < 1.0:
        return False, ""
    code = clean_source([_extract_code(res.answer)] + executed, spec.get("entry", ""))
    return True, code


def mine(suites: list[str], model: str | None) -> None:
    backend = get_backend(model)
    plain = Agent(backend, max_steps=8)
    strong = Orchestrator(backend, max_steps=12)
    bon = BestOfN(backend, n=3, max_steps=10)
    store = GoldStore()
    mined = attempted = recovered = 0

    for suite in suites:
        for task in load_suite(suite):
            spec = task["score"]
            if spec.get("type") != "code_test":
                continue  # only mine verifiable coding tasks
            attempted += 1
            # 1) plain agent
            ok, _ = _passed(plain.run(task["prompt"]), spec)
            if ok:
                continue  # base already solves it — not a weak spot
            print(f"  [{task['id']}] base FAILED — retrying with stronger solvers...")
            # 2) escalate: critic, then best-of-N
            code = ""
            for solver in (strong, bon):
                ok, code = _passed(solver.run(task["prompt"]), spec)
                if ok:
                    recovered += 1
                    break
            if not ok or not code:
                print(f"      still unsolved — left for fine-tuning/bigger model.")
                continue
            # 3) store the recovered hard example as gold training data
            ex = Example(
                instruction=task["prompt"], answer=code, tests=spec["tests"],
                category=task.get("category", suite),
                difficulty=max(task.get("difficulty", 3), estimate_difficulty(code, spec["tests"])),
                quality=max(0.8, quality(task["prompt"], code, spec["tests"], True)),
                source="mined-failure", verified=True)
            if store.add(ex):
                mined += 1
                print(f"      RECOVERED + stored (hard example, d{ex.difficulty}).")

    print(f"\nattempted {attempted} | base failures recovered {recovered} | "
          f"new gold examples {mined} | store now {len(store)}")
    print("These target the model's REAL weak spots. Next: prepare + qlora on them.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", nargs="*", default=["coding", "agent"])
    ap.add_argument("--model", default=None)
    a = ap.parse_args()
    print(f"=== Mining failures from {a.suites} ===")
    mine(a.suites, a.model)


if __name__ == "__main__":
    main()
