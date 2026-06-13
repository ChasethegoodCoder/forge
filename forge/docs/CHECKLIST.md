# Forge Build Checklist — Coding-First

**Identity:** Forge is optimized to be *great at coding*, secondarily good at reasoning.
Chat is a thin convenience layer, not the goal. Every benchmark and lever below is
weighted toward code correctness.

Legend: [x] done · [~] in progress · [ ] todo

## Foundation (Phase 1 — Stage 1)
- [x] Hardware/current-state report (real specs)
- [x] Local engine via Ollama (Qwen2.5-7B)
- [x] Swappable backend interface
- [x] ReAct agent loop with JSON action protocol
- [x] Tools: read_file, write_file, list_files, run_python, run_shell
- [x] JSON memory (v0)
- [x] CLI: solve / chat / bench / report
- [x] Deterministic benchmark + judge + progress ledger
- [x] First measured baseline (81.8% on v1 suite)
- [x] Phase docs: current-state, target, gap, roadmap, improvement queue

## Coding-first push (this milestone)
- [x] Expand coding suite to 20 tasks (alg/string/list/edge cases)
- [x] Self-verification pass: agent must run code before finalizing
- [~] Pull Qwen2.5-**Coder**-7B (specialized for code) — downloading
- [ ] Head-to-head: qwen2.5 vs qwen2.5-coder on the suite → pick winner as default
- [ ] Set coding-tuned defaults (low temperature, coder model)

## Next (Stage 2–3)
- [ ] Add a hard coding suite (multi-function, classes, debugging-a-broken-file tasks)
- [ ] Held-out test set (never used for tuning) to prevent overfitting
- [ ] web_search / web_fetch tools (Research axis)
- [ ] Semantic memory (embeddings + vector recall)

## Later (Stage 6+ — needs the above proven first)
- [ ] Dataset Factory: generate + filter coding examples locally
- [ ] QLoRA fine-tune Qwen2.5-Coder-7B on failures (fits your 12 GB)
- [ ] Multi-agent: planner / coder / critic roles
- [ ] Self-improvement flywheel (auto mine failures → retrain → re-measure)
- [ ] Scale test: 14B-Q4

## Current capabilities (multimodal, local, on 14B)
- [x] Chat + code (auto-routing), works on REAL folders (`--project`)
- [x] Multi-file project builder (plan → master each file → integrate → escalate)
- [x] Vision input (`image`) — llama3.2-vision:11b
- [x] Local asset generation (`asset`) — Stable Diffusion sd-turbo; SDXL optional
- [x] Online asset download (`download_asset` tool) — Kenney/CC0 packs
- [x] Asset strategy baked in: code-drawn for geometric, SD for art, download for packs
- [x] Conversation memory across sessions (semantic recall)
- [x] Clarifying questions (options + Other)
- [x] Self-debug (targeted error context + completeness gate)
- [x] Escalation hook (hard steps → bigger/rented model via `engine.big_model`)
- [x] 15 tools; `help` lists all commands
- [ ] Phase D (documents: create + search) · Phase F (UI — user designing)

## What YOU need to do
**Nothing required.** The coder-model download runs in the background. If you ever
want to drive it yourself: `cd forge && python cli.py bench` then `python cli.py report`.
Optional: if a download stalls, re-run `ollama pull qwen2.5-coder:7b-instruct`.
