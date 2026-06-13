"""Head-to-head: run the same suite through multiple models, print per-task,
and a final comparison table. Unbuffered so progress streams to the log."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.agent import Agent
from forge.backend import get_backend
from bench.harness import load_suite
from bench.judge import score_one

MODELS = ["qwen2.5:7b-instruct", "qwen2.5-coder:7b-instruct"]
SUITES = ["coding", "reasoning"]
MAX_STEPS = 12

def run_model(model):
    agent = Agent(get_backend(model), max_steps=MAX_STEPS)
    rows = []
    for suite in SUITES:
        for task in load_suite(suite):
            t0 = time.time()
            res = agent.run(task["prompt"])
            executed = [s.args.get("code", "") for s in res.steps
                        if s.action == "run_python" and isinstance(s.args, dict)]
            sc, note = score_one(res.answer, task["score"], extra_code=executed)
            dt = time.time() - t0
            rows.append((task["id"], task.get("category", suite), sc, res.stopped_reason, dt))
            mark = "PASS" if sc >= 1 else "FAIL"
            print(f"  [{mark}] {task['id']:<8} {sc:.0f} {res.stopped_reason:<6} {dt:5.1f}s {note[:40]}", flush=True)
    return rows

results = {}
for m in MODELS:
    print(f"\n===== {m} (max_steps={MAX_STEPS}) =====", flush=True)
    results[m] = run_model(m)

print("\n\n========== COMPARISON ==========", flush=True)
for m, rows in results.items():
    overall = sum(r[2] for r in rows) / len(rows)
    cod = [r[2] for r in rows if r[1] == "coding"]
    secs = sum(r[4] for r in rows)
    coding = sum(cod)/len(cod) if cod else 0
    budget = sum(1 for r in rows if r[3] == "budget")
    print(f"{m:<30} overall={overall*100:5.1f}%  coding={coding*100:5.1f}%  "
          f"budget_hits={budget}  total={secs:5.0f}s", flush=True)
