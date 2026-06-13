# Phase 5 — Roadmap (Current State → Target)

Each stage: **Purpose · Benefit · Requirements · Risks · Code required.** Stages are
ordered by the Gap Report's priority: cheap harness wins first, deep weight-level
levers later. Status: [x] done · [~] doing · [ ] todo.

---

### Stage 1 — Foundation [x]
- **Purpose:** runnable agent loop + benchmark + progress ledger.
- **Benefit:** every later change is measurable. No measurement = no project.
- **Requirements:** Ollama, Qwen2.5, `requests`.
- **Risks:** model malforms JSON actions → mitigated by tolerant parser.
- **Code:** `forge/backend.py`, `forge/agent.py`, `forge/tools/*`, `bench/*`. **Built.**

### Stage 2 — Tools [~] (next)
- **Purpose:** add web-search + fetch, structured-output validation, a diff/patch tool.
- **Benefit:** unlocks Research axis (gap 85) and stronger tool use (gap 55).
- **Requirements:** a free search source (DuckDuckGo HTML / SearXNG local); `requests`.
- **Risks:** rate limits, parsing noise → cache results, validate args before dispatch.
- **Code:** `forge/tools/web.py`, arg-schema validation in `tools/__init__.py`.

### Stage 3 — Memory ⬜
- **Purpose:** semantic memory via embeddings + vector recall.
- **Benefit:** continuity across long tasks/sessions (gap 80).
- **Requirements:** `sentence-transformers`, `chromadb` (both run on your GPU/CPU).
- **Risks:** retrieval injecting irrelevant context → relevance threshold + recency.
- **Code:** swap `forge/memory.py` backend; keep the same `remember/recall` interface.

### Stage 4 — Data Generation ⬜
- **Purpose:** the Dataset Factory (Phase 7) — generate + score training examples.
- **Benefit:** fuel for fine-tuning; also expands the benchmark.
- **Requirements:** the agent itself as generator; the judge as filter.
- **Risks:** low-quality self-generated data → quality-score gate, dedup, human spot-check.
- **Code:** `factory/generate.py`, `factory/filter.py` (Phase 7 stub planned).

### Stage 5 — Evaluation ⬜ (deepen)
- **Purpose:** grow benchmark coverage; add a rubric LLM-judge for open-ended tasks.
- **Benefit:** measures Writing/Planning that exact-match can't score.
- **Requirements:** local model as judge (no API, per project rule).
- **Risks:** noisy local judge → pairwise comparison + multiple samples.
- **Code:** `bench/judge.py` (extend), `bench/tasks/*` (add suites).

### Stage 6 — Fine-Tuning ⬜
- **Purpose:** QLoRA-train Qwen2.5-7B on filtered self-data + failure cases.
- **Benefit:** raises the hard floor on Coding/Reasoning/Instruction-Following.
- **Requirements:** `torch, transformers, peft, trl, bitsandbytes` — all fit 12 GB at 4-bit.
- **Risks:** overfitting / catastrophic forgetting → small LR, eval-gated, keep base as fallback.
- **Code:** `train/qlora.py`, `train/dataset.py`, eval-before-promote gate.

### Stage 7 — Agents ⬜
- **Purpose:** multi-agent roles (planner / coder / critic) over the same backend.
- **Benefit:** division of labor recovers capability a single 7B pass can't.
- **Requirements:** Stage 1 loop generalized to roles.
- **Risks:** coordination overhead, loops → step budgets + a controller.
- **Code:** `forge/agents/{planner,coder,critic}.py`, `forge/orchestrator.py`.

### Stage 8 — Self-Improvement ⬜ (partially via Phase 9 loop)
- **Purpose:** automated failure mining → new training/eval tasks → retrain → re-measure.
- **Benefit:** the flywheel; compounding gains without manual labor.
- **Requirements:** Stages 4–6 working.
- **Risks:** reward hacking the benchmark → hold-out test set never trained on.
- **Code:** `loop/improve.py` reading `bench/results/history.jsonl`.

### Stage 9 — Scaling ⬜
- **Purpose:** move to Qwen2.5-14B-Q4, raise context, batch eval.
- **Benefit:** higher ceiling within the 12 GB budget.
- **Risks:** slower inference → quantization + caching.
- **Code:** config change + perf passes.

### Stage 10 — Advanced Architectures ⬜
- **Purpose:** retrieval-augmented reasoning, tree/graph search over steps, tool-former-style learned tool use.
- **Benefit:** closes the long tail on hard reasoning.
- **Risks:** complexity > benefit → gate every addition on the benchmark.
- **Code:** experimental; only merged if the ledger moves.

---

**Governing rule:** a stage is "done" only when `python cli.py report` shows the
benchmark moved. Engineering that doesn't move the number is reverted.
