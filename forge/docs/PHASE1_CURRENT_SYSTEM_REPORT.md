# Phase 1 — Current System Report

_Generated 2026-06-12. Hardware figures are measured on this machine, not estimated._

## 1. Inventory (measured)

| Item | Value | Source |
|---|---|---|
| **CPU** | AMD Ryzen 7 7800X3D, 8 cores / 16 threads | `Win32_Processor` |
| **RAM** | 32 GB (31.2 GB usable) | `Win32_ComputerSystem` |
| **GPU** | NVIDIA RTX 4070 SUPER, **12 GB VRAM** | `nvidia-smi` (WMI misreports 4 GB — ignore it) |
| **Storage** | ~550 GB free C:, ~520 GB free G: | `Win32_LogicalDisk` |
| **OS / Python** | Windows 11 Pro / Python 3.12.4 | runtime |
| **Runtime** | Ollama 0.30.8 | `ollama --version` |
| **Engine model** | Qwen2.5-7B-Instruct (Apache-2.0) | chosen; 14B-Q4 also viable |
| **Datasets** | none yet (Phase 7 will generate them) | — |
| **Tooling** | Forge harness v0.1: agent loop, 4 tools, JSON memory, benchmark suite | this repo |

## 2. The hardware envelope (what this rig can and cannot do)
- **Inference:** comfortably runs 7–8B at full quality; up to ~14B at 4-bit quant.
- **Fine-tuning:** QLoRA on 7B fits in 12 GB. Full fine-tune / >14B: out of reach.
- **Frontier training:** impossible at this scale, and that's fine — not the goal.

## 3. Current limitations (honest)
1. **Raw reasoning ceiling** of a 7B model is well below Sonnet 4.6. Permanent at this tier; mitigated by harness + verification, not eliminated.
2. **No persistent semantic memory yet** (JSON key/value only). Phase 3.
3. **No self-critique / multi-pass** in the loop yet. Phase 8.
4. **Tool set is minimal** (files, python, shell). Web/research absent. Phase 2 of roadmap.
5. **No fine-tuning data** — the model is stock. Phases 6–7.

## 4. Capability scores (0–100) — PRE-benchmark estimates

These are honest engineering estimates for **Qwen2.5-7B + Forge harness v0**,
relative to Sonnet 4.6 = 100 on each axis. They are placeholders until
`python cli.py bench` replaces the measurable ones with real numbers.

| Capability | Score | Why this number |
|---|---:|---|
| **Reasoning** | 42 | Solid on 1–2 step problems; degrades on multi-hop/abstract logic. Verification tool lifts effective score. |
| **Coding** | 50 | Qwen2.5 codes well at small scale; passes easy/medium function tasks, struggles on multi-file & subtle edge cases. |
| **Planning** | 35 | Agent loop gives basic decomposition; no explicit planner or backtracking yet. |
| **Writing** | 48 | Fluent, coherent prose; weaker at long-form structure and precise instruction adherence. |
| **Tool Use** | 45 | JSON-protocol tool calls work, but 7B occasionally malforms args or loops. |
| **Research** | 15 | No web/retrieval tools yet — near-zero by design until added. |
| **Memory** | 20 | Only flat JSON recall; no semantic retrieval. |
| **Agent Behavior** | 38 | Completes simple multi-step tasks; weak failure recovery and no self-check. |

**Composite (unweighted): ~36 / 100.** Read this as: a capable assistant on
narrow tasks, far from the target on open-ended agentic work. The benchmark exists
to turn these guesses into tracked facts.

## 5. First measurable baseline
Run `python cli.py bench`. The result lands in `bench/results/history.jsonl` and
becomes run #1 of the progress ledger. Every future change is judged against it.
