# Phase 3 — Gap Report

Current (Forge v0, Qwen2.5-7B) vs Target (Sonnet 4.6 = 100). Ranked by **priority**
= (gap size × leverage on this hardware) ÷ difficulty. High priority = do first.

| Rank | Capability | Current | Target | Gap | Difficulty | Est. time | Priority | Lever |
|---:|---|---:|---:|---:|---|---|---|---|
| 1 | **Self-Critique** | 25 | 100 | 75 | Low | 1–2 days | **HIGH** | Harness: add verify/critique pass |
| 2 | **Tool Use** | 45 | 100 | 55 | Low | 1–3 days | **HIGH** | Harness: more tools + better arg validation |
| 3 | **Research** | 15 | 100 | 85 | Med | 3–5 days | **HIGH** | Add web-search + fetch tools |
| 4 | **Memory** | 20 | 100 | 80 | Med | 3–5 days | **HIGH** | Embeddings + vector recall (Phase 3 roadmap) |
| 5 | **Planning** | 35 | 100 | 65 | Med | 3–6 days | MED | Explicit planner + replan-on-failure |
| 6 | **Agent Behavior** | 38 | 100 | 62 | Med | ongoing | MED | Recovery, stop/ask heuristics |
| 7 | **Multi-Step Tasks** | 35 | 100 | 65 | Med | ongoing | MED | Emerges from 1,5,6 |
| 8 | **Coding** | 50 | 100 | 50 | High | weeks | MED | Verification now; QLoRA later |
| 9 | **Reasoning** | 42 | 100 | 58 | High | weeks | LOW* | Hard floor; fine-tune + best 14B model |
| 10 | **Writing** | 48 | 100 | 52 | High | weeks | LOW | Lower ROI; revisit after core agent |
| 11 | **Long Context** | 40 | 100 | 60 | Med | depends | LOW | Raise num_ctx; bigger model; chunking |
| 12 | **Instruction Following** | 50 | 100 | 50 | Med | ongoing | MED | Prompt discipline + fine-tune |

\* *Low priority ≠ unimportant.* Reasoning is the most valuable axis but the
**hardest and slowest** to move on this hardware, so we attack cheap harness wins
first (ranks 1–4) that raise *effective* end-to-end scores fastest, then return to
the deep levers (coding/reasoning fine-tuning) once measurement infrastructure proves them out.

## Sequenced conclusion
**Do ranks 1–4 first** (self-critique, tool use, research, memory). They're low/medium
difficulty, high leverage, and they lift the *whole-system* benchmark — which is the
number that actually defines "closing the gap." This ordering is what Phase 5's
roadmap encodes.
