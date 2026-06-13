# Making Forge Smarter — going beyond 7B

You asked: *is there any way to make it smarter and train it (over 7B)?* Yes — three
real levers, all on YOUR hardware (RTX 4070, 12 GB), all free. Ordered by effort.

## Lever 1 — Run a bigger model (immediate, zero training)
The 4070's 12 GB fits more than 7B:

| Model | Quant | ~VRAM | Fits? | Notes |
|---|---|---|---|---|
| Qwen2.5-7B | full/Q8 | ~5–8 GB | ✅ easy | current default, fast |
| **Qwen2.5-14B** | **Q4_K_M** | **~9 GB** | ✅ **yes** | **~2× the params, clearly smarter; pulling now** |
| Qwen2.5-32B | Q3 | ~15 GB | ⚠️ partial | needs CPU offload → slow but runnable |
| Qwen2.5-Coder-14B | Q4 | ~9 GB | ✅ yes | code-specialized 14B |

How: `ollama pull qwen2.5:14b-instruct-q4_K_M`, then set `engine.model` in
`config/forge.yaml`. The whole harness uses it instantly (swappable-backend design).
Cost: slower per token (bigger model), but higher quality. We **measure** the trade
with the benchmark, not guess.

## Lever 2 — Train your own model (QLoRA — "over 7B" in capability, not size)
A fine-tuned 7B can BEAT a stock 14B *on your target domain* (coding). The pipeline is
already built (`forge/train/`):
1. `python -m forge.factory.generate --n 300` — make verified training data (have 7 so far)
2. `python -m forge.train.prepare` — format it
3. `pip install torch transformers peft trl bitsandbytes accelerate datasets`
4. `python -m forge.train.qlora` — 4-bit QLoRA, fits 12 GB, ~1–3 GPU-hours
5. Export adapter → GGUF → `ollama create forge-v1` → it becomes a model you own
6. **Eval-gate**: only promote if it beats current on held-out HumanEval

This is true "training it." You can fine-tune the 7B *or the 14B* the same way.

## Lever 3 — Spend more inference compute (harness scaling)
Make a fixed model act smarter by doing more at inference (already partly built):
- **Critic/orchestrator** (built): coder + reviewer + revision.
- **Best-of-N**: generate N solutions, keep the one that passes its own tests.
- **Multi-agent**: planner → coder → critic as separate focused calls.
These trade time for quality and shine on hard, multi-step tasks.

## The honest ceiling
Even 14B + QLoRA + harness will **not equal Sonnet 4.6 on open-domain reasoning** —
that needs frontier-scale weights. But on **coding specifically**, this stack can close
much of the 12-point HumanEval gap and, on multi-file agentic tasks, the harness is
where most of the remaining distance lives. Forge's bet: get excellent at coding, accept
the open-domain gap.

## Recommended order
1. Benchmark **14B vs 7B** (pulling now) → adopt 14B if the score gain beats the slowdown.
2. Grow the **gold dataset** (factory) to a few hundred verified examples.
3. **QLoRA fine-tune** the chosen base on that data; eval-gate promotion.
4. Build the **P15 multi-file benchmark** so harness gains become visible.
5. Turn on the **continuous loop** (`forge/improve.py`) to repeat 2–4 automatically.
