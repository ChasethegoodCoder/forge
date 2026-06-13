# Forge Master Checklist & Status

The single source of truth for the whole project. Coding-first identity.
Status legend: **[x] done** · **[~] partial / v0** · **[ ] not started**
Owner: **F** = Forge/automation builds it · **H** = needs you (human) · **M** = me (the assistant) drives it

---

## A. Coverage map — your 24 requested components
Every item you listed, mapped to a phase and its current status.

| # | Component | Status | Phase | Where |
|--:|---|:--:|:--:|---|
| 1 | System prompt / identity setup | [x] | P0 | `forge/agent.py` SYSTEM_TEMPLATE (coding-first) |
| 2 | Current-state analysis (model/hw/limits) | [x] | P1 | `docs/PHASE1_CURRENT_SYSTEM_REPORT.md` |
| 3 | Capability scoring | [x] | P1 | PHASE1 report (+ measured by benchmark) |
| 4 | Target analysis (Sonnet 4.6 breakdown) | [x] | P2 | `docs/PHASE2_TARGET_ANALYSIS.md` |
| 5 | Gap analysis (current vs target) | [x] | P2 | `docs/PHASE3_GAP_REPORT.md` |
| 6 | Benchmark design (reason/code/write/agent) | [~] | P3 | code+reason done; write+agent suites TODO |
| 7 | Evaluation system (auto scoring) | [x] | P3 | `bench/judge.py` (deterministic) |
| 8 | Master roadmap | [x] | P0 | `docs/PHASE5_ROADMAP.md` + this file |
| 9 | Project infrastructure (folders/tools/pipeline) | [x] | P0 | repo layout + `cli.py` |
| 10 | Dataset factory (synthetic data) | [ ] | P7 | not started |
| 11 | Automatic code-gen system | [~] | P4 | the agent writes/edits/runs code; no self-build orchestration |
| 12 | Self-critique system | [~] | P6 | verify-gate done; full critic role TODO |
| 13 | Improvement loop (detect→fix→retrain) | [~] | P6 | manual queue done; auto loop TODO |
| 14 | Data accumulation (store best only) | [ ] | P7 | not started |
| 15 | Fine-tuning pipeline (LoRA/QLoRA) | [ ] | P8 | not started (deps listed) |
| 16 | Agent system (planner/coder/critic) | [ ] | P9 | not started |
| 17 | Memory system (long-term + project) | [~] | P5 | JSON v0 done; semantic TODO |
| 18 | Tool integration (search/exec/files) | [~] | P4 | files+exec+shell done; web search TODO |
| 19 | Benchmark tracking over time | [x] | P3 | `bench/results/history.jsonl` + `report.py` |
| 20 | Scaling strategy (bigger models) | [~] | P11 | plan done; 14B test pending |
| 21 | Continuous retraining cycle | [ ] | P10 | not started |
| 22 | Research mode (experiments/hypotheses) | [ ] | P10 | not started |
| 23 | Autonomous improvement suggestions | [~] | P10 | manual `PHASE9_IMPROVEMENT_QUEUE.md`; auto TODO |
| 24 | Human-in-the-loop review | [~] | P12 | you approve via git; no formal gate yet |

**Tally: 9 done · 8 partial · 7 not started.**

---

## B. Phases — what's done, what's needed

### Phase 0 — Identity & Infrastructure  ✅ DONE
- **Done:** coding-first system prompt; repo layout (`forge/`, `bench/`, `docs/`, `config/`); swappable backend; CLI (`solve/chat/bench/report`); git.
- **Need:** nothing. Revisit prompt as capabilities grow.
- Owner: M.

### Phase 1 — Current-State & Capability Analysis  ✅ DONE
- **Done:** real hardware report (RTX 4070 SUPER 12GB, 7800X3D, 32GB); limitations; capability scores (estimated + now measured).
- **Need:** re-score automatically after each benchmark (small enhancement).
- Owner: M/F.

### Phase 2 — Target & Gap Analysis  ✅ DONE
- **Done:** Sonnet 4.6 capability breakdown; ranked gap report with priorities.
- **Need:** refresh numbers as the benchmark grows.
- Owner: M.

### Phase 3 — Benchmark & Evaluation  🟡 PARTIAL → highest near-term value
- **Done:** deterministic auto-scorer (numeric/exact/contains/code_test); 20 coding + 6 reasoning tasks; executed-code fallback scoring; progress ledger + report; **historical tracking**.
- **Need:**
  - [ ] **Writing** suite (rubric-scored by a local LLM-judge — no API, per project rule).
  - [ ] **Agent** suite (multi-step tasks: build X, fix a broken file, use tools).
  - [ ] Grow to ~40–60 tasks so scores are statistically stable.
  - [ ] **Held-out test set** never used for tuning (overfitting guard before P8).
- Owner: M/F.

### Phase 4 — Agent Harness & Tools  🟡 PARTIAL
- **Done:** ReAct loop; JSON action protocol; tools = read/write/list files, run_python, run_shell; verify-gate; low-temp coding mode.
- **Need:**
  - [ ] `web_search` + `web_fetch` (free source: DuckDuckGo HTML / local SearXNG) → unlocks Research axis (currently ~15/100).
  - [ ] `apply_patch`/diff tool for multi-file edits.
  - [ ] Arg-schema validation before dispatch (fewer malformed calls).
- Owner: F.

### Phase 5 — Memory  🟡 PARTIAL (v0)
- **Done:** JSON key/value + event log; stable `remember/recall` interface.
- **Need:**
  - [ ] Semantic memory: `sentence-transformers` embeddings + `chromadb` vector recall (runs on your GPU).
  - [ ] Project memory: per-task scratchpad the agent reads/writes across steps.
- Owner: F.

### Phase 6 — Self-Critique & Improvement Loop  🟡 PARTIAL
- **Done:** verify-gate (must run code before finalizing); manual improvement queue mined from runs.
- **Need:**
  - [ ] **Critic pass**: a second model call scores the answer (correctness/edge-cases) and sends fixes back before finalize.
  - [ ] **Auto loop**: failing benchmark tasks → logged as structured "weakness" records → become new training/eval items.
- Owner: F.

### Phase 7 — Dataset Factory & Data Accumulation  ⬜ NOT STARTED
- **Need:**
  - [ ] `factory/generate.py`: agent generates coding problems + reference solutions.
  - [ ] `factory/filter.py`: judge runs the solution's tests; keep only verified, deduped, high-quality examples ("store best only").
  - [ ] Accumulating store: `data/gold/*.jsonl` with instruction/answer/reasoning/difficulty/category/quality fields (your Phase 7 schema).
- Owner: F.

### Phase 8 — Fine-Tuning Pipeline (QLoRA)  ⬜ NOT STARTED
- **Need:**
  - [ ] `train/qlora.py` (peft+trl+bitsandbytes; 4-bit, fits 12GB on 7B).
  - [ ] Train on gold data + mined failures.
  - [ ] **Eval-gated promotion**: a new checkpoint replaces the default ONLY if it beats current on the held-out set. Keep base as fallback.
  - [ ] Export to GGUF → serve via Ollama (closes the loop: your own weights, locally).
- Owner: F, **H to start the GPU run** (long-running).

### Phase 9 — Multi-Agent System  ⬜ NOT STARTED
- **Need:** `planner` (decompose) → `coder` (implement+verify) → `critic` (review) over the same local backend, with an `orchestrator` + step budgets. Division of labor recovers capability a single 7B pass can't.
- Owner: F.

### Phase 10 — Autonomy: Research Mode, Auto-Suggestions, Continuous Loop  ⬜ NOT STARTED
- **Need:**
  - [ ] Research mode: propose hypotheses ("does critic pass raise coding 5pts?"), run as A/B benchmark experiments, log results.
  - [ ] Autonomous suggestions: scan ledger + failures → propose ranked upgrades (extends PHASE9 queue automatically).
  - [ ] Continuous evolution loop: measure → improve → (retrain) → re-measure, repeating, with every change gated on the ledger.
- Owner: F, gated by H approval.

### Phase 11 — Scaling Strategy  🟡 PARTIAL
- **Done:** documented path (14B-Q4 within 12GB; raise context; caching).
- **Need:** [ ] benchmark `qwen2.5:14b-instruct-q4_K_M` vs 7B; adopt if score/latency tradeoff is worth it.
- Owner: M/F.

### Phase 12 — Safety, Sandbox & Human-in-the-Loop  🟡 PARTIAL  *(added)*
- **Done:** workspace-sandboxed file tools; shell marked dangerous; subprocess timeouts.
- **Need:**
  - [ ] Harden code execution (resource limits / container) before any unattended autonomy.
  - [ ] Formal approval gate: autonomous changes open a diff you approve before merge.
- Owner: F + H.

### Phase 13 — Reproducibility & Regression CI  ⬜ NOT STARTED  *(added)*
- **Need:**
  - [ ] Pin model + seed + suite version in every ledger record (partly there).
  - [ ] One command that runs the full suite and flags any category regression vs last run (guards the "improve forever" loop against silent backsliding).
- Owner: F.

---

## C. What YOU (H) need to do
1. **Nothing to keep current progress moving** — Forge runs locally and I drive it.
2. **One decision when we reach Phase 8:** approve kicking off a multi-hour QLoRA training run on your GPU (it'll occupy the 4070).
3. **Approvals:** when autonomy (P10) is on, you review/approve proposed changes. Until then I report each step.

## D. Recommended next 3 moves (in order)
1. **Finish Phase 3** — add the Agent + Writing suites and grow to ~40 tasks (makes every later number trustworthy). 
2. **Phase 4 web tools** — biggest single capability gap (Research ~15/100) and cheap to add.
3. **Phase 6 critic pass** — directly raises coding/reasoning correctness, measurable immediately.

> Governing rule (unchanged): a change is "done" only when `python cli.py report` shows the benchmark moved. If the number doesn't move, we revert.
