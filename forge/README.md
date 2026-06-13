# Project Forge

A **local-first, free-forever** agentic AI system. The mission: climb measurably
toward **Sonnet-4.6-level task performance** on a defined benchmark suite — using
open-weights models you own, running on your own GPU, with no API keys.

## The honest thesis
A 7–14B local model will not equal Sonnet 4.6's raw reasoning. But *task
performance* is `weights × harness × fine-tuning × orchestration`, and you fully
control three of those four factors. Forge invests there and **measures every
change** against the target. If a change doesn't move the benchmark, it didn't help.

## Stack
- **Engine:** Ollama + Qwen2.5 (Apache-2.0 — you own it). 7B default; 14B-Q4 fits 12 GB.
- **Harness:** ReAct agent loop, tool registry, JSON memory (this repo, pure Python).
- **Measurement:** deterministic benchmark suite + progress ledger.

## Setup
```bash
# 1. Ollama (native install) is already present. Pull the engine:
ollama pull qwen2.5:7b-instruct

# 2. Python deps (just `requests` for now):
pip install -r requirements.txt
```

## Use
```bash
python cli.py solve "Compute the 10th Fibonacci number and verify it."
python cli.py chat                       # interactive agent
python cli.py bench                       # homemade quick suite -> history.jsonl
python cli.py humaneval --limit 20        # STANDARD benchmark vs Sonnet 4.6 (92%)
python cli.py humaneval --limit 164 --k 1 # full official HumanEval run
python cli.py report                      # progress vs target over time
```

**HumanEval is the real yardstick:** it's a published benchmark whose Sonnet 4.6
score (~92% pass@1) is known, so the gap Forge reports is comparable to the actual
target. Scoring is file-based (the agent writes `solution.py`; the official test runs
against it) — no fragile output parsing.

## Harness (the Claude-Code-style part)
Forge's power comes from the harness around the model, not the weights:
- **9 tools:** `read_file` `write_file` `list_files` `edit_file` (surgical) `grep`
  `glob_files` `run_python` `run_shell` `update_plan`.
- **Operating principles** baked into the system prompt: understand → plan → edit
  surgically → verify by running → self-critique → act decisively.
- **Multi-agent** (`forge/orchestrator.py`): coder + strict critic + one revision.
  Try it: `python cli.py humaneval --limit 20 --critic`.

## Layout
```
forge/
  forge/        core: backend (engine), agent (loop), orchestrator, tools/, memory
  bench/        measurement: tasks/, data/ (HumanEval), judge, harness, humaneval, report
  docs/         reports: current-state, target, gap, roadmap, checklist, forge-vs-claude
  config/       forge.yaml
  cli.py        entry point
```

## Where we are
Phase 1 complete (current-state report + runnable harness). See `docs/`.
Next action is always: **run `python cli.py bench`, then attack the lowest-scoring
category.** The roadmap in `docs/PHASE5_ROADMAP.md` orders the work.
