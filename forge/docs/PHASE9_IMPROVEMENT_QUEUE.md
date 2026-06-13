# Phase 9 — Self-Improvement Queue

Living document. Each benchmark run mines failures into prioritized work. Newest first.

## Run log
| # | Date | Model | Overall | Notes |
|--:|---|---|---:|---|
| 1 | 2026-06-13 | qwen2.5:7b | 63.6% | first baseline; eval-extraction bug undercounted coding |
| 2 | 2026-06-13 | qwen2.5:7b | **81.8%** | fixed judge `_extract_code` (literal `\n` escapes) → coding 50%→100% |

## HumanEval (standard benchmark, vs Sonnet 4.6 = 92% pass@1)
| Date | Mode | pass@1 | Time | Notes |
|---|---|---:|---:|---|
| 2026-06-13 | agent (full harness) | **80.0%** | 728s | n=20; gap 12 pts to target |
| 2026-06-13 | raw (single-pass) | **80.0%** | 66s | n=20; same score, **11× faster** |

### ⭐ Key finding (run this honestly): the harness does NOT help on HumanEval
Raw and agent score identically (80%), but the harness is 11× slower. Conclusion:
**single-function problems don't exercise what the harness is for** (planning, multi-file,
tools, memory). The raw 7B already solves them. This is not a harness failure — it's a
benchmark-coverage gap.
**Implication:** to *measure* harness value we need harder, multi-step / multi-file
tasks (P15, SWE-bench-style). Until then, use `--mode raw` for fast coding baselines.
The 3 agent-mode-only failures were budget/over-working artifacts the raw mode avoids.

## Findings from run #2
**Successes**
- Coding suite 100% (5/5). Qwen2.5-7B writes correct functions reliably.
- Math 100%. Verification-via-`run_python` works.

**Failures (real, model-level)**
- `rsn-002` bat-and-ball: answered $0.10 (intuitive trap) instead of $0.05. Classic System-1 error — the model didn't verify algebraically.
- `rsn-006` light-switch puzzle: answered 2 vs expected 1 (heat-trick). Lateral reasoning gap (answer key is the "trick" solution — borderline).

**Process finding**
- The benchmark caught a crash (bare-int action) AND a silent scoring bug (escaped newlines). *The measurement layer needs hardening as much as the model* — a noisy ruler hides real progress.

## Prioritized queue
| P | Type | Task | Rationale | Target axis |
|--:|---|---|---|---|
| 1 | Harness | Add a **self-critique pass**: before `final`, force the agent to re-check reasoning answers with `run_python`/algebra. | Would have caught bat-and-ball. Cheapest win. | Self-Critique, Reasoning |
| 2 | Eval | Expand suites to ~40 tasks (more reasoning/logic) so scores are statistically meaningful. | 11 tasks is too few; one fail = 9%. | Measurement quality |
| 3 | Tools | Add `web_search`/`web_fetch` (Stage 2). | Research axis is at 15 — biggest untouched gap. | Research, Tool Use |
| 4 | Eval | Add a held-out test set never used for tuning. | Prevent benchmark overfitting before Stage 6. | Integrity |
| 5 | Engine | Trial `qwen2.5:14b-instruct-q4_K_M` on the same suite; compare cost/score. | Cheap ceiling test within 12 GB. | Reasoning, Coding |

## Next action
Implement P1 (self-critique pass in `forge/agent.py`) and re-run `python cli.py bench`.
If overall rises, keep it; if not, revert. The ledger decides.
