# The big-model ladder — from "beat old DeepSeek" to ~1T

Goal: run progressively bigger models by renting bigger nodes. Forge's swappable backend
runs on ALL of them unchanged — you just point `FORGE_HOST` at the box. Memory rule:
**VRAM needed ≈ params × 0.5 (at 4-bit) × ~1.2 overhead.** MoE models store all params but
only compute a few per token, so they're cheaper to RUN than their size suggests.

## The rungs

| Rung | Model (open weights) | Params | VRAM @4-bit | GPUs to rent | ~$/hr |
|---|---|---|---|---|---|
| 0 (now) | Qwen2.5-7B | 7B | ~5 GB | your 4070 | $0 |
| **1 — beat old DeepSeek** | **Qwen2.5-72B** / Llama-3.3-70B | 70-72B | ~45 GB | **1× A100/H100 80GB** | **~$2-4** |
| 2 | DeepSeek-V2 / Coder-V2 (old DeepSeek itself) | 236B MoE (21B active) | ~130 GB | 2× A100/H100 80GB | ~$5-9 |
| 3 | **DeepSeek-V3 / R1** (current DeepSeek) | 671B MoE (37B active) | ~340 GB | **8× H100 80GB node** (640 GB) | ~$20-30 |
| **4 — ~1T** | **Kimi K2** (Moonshot) | **~1T MoE** (~32B active) | ~550 GB | **8× H100** (640 GB) or 8× H200 | ~$20-35 |
| 5 — beyond | Llama 4 Behemoth-class | ~2T | ~1 TB+ | 16× H100 (multi-node) | ~$50-80 |

## Reading the ladder
- **Rung 1 already beats "old DeepSeek."** Qwen2.5-72B / Llama-3.3-70B outscore
  DeepSeek-Coder-V2-era models on coding, and run on a **single** 80 GB GPU for ~$2-4/hr.
  That's your cheapest, fastest win — a model far stronger than your 7B, today.
- **Rung 3-4 is where "1T" actually lives.** Thanks to MoE, a ~1T model (Kimi K2) only
  activates ~32B params per token, so a standard **8×H100 node (640 GB)** runs it at
  4-bit. ~1T is *rentable*, not mythical — ~$20-35/hr while it's on.
- **Rung 5 (2T+)** needs multiple nodes; open options are thin and it's costly. Possible,
  rarely worth it for one person.

## What you CAN'T do (the honest line)
- **Train** any of these from scratch — that's thousands of GPUs for months, $tens of
  millions, frontier labs only. You RENT and RUN them; you don't build them.
- **Run 1T on your 4070** — physically impossible (needs ~550 GB; you have 12 GB). The
  ladder is entirely about *renting* the memory, not owning it.

## How each rung connects to Forge (identical every time)
1. Rent the node (RunPod/Lambda), SSH in.
2. Serve the model: `vllm serve <model>` (vLLM handles multi-GPU sharding) or Ollama.
3. On your PC: `FORGE_HOST=http://<box>:8000 FORGE_MODEL=<model> python cli.py ping`.
4. Your whole harness — tools, critic, memory, benchmarks — now runs on that brain.

> vLLM is the better server for big multi-GPU models (tensor-parallel across the 8 GPUs);
> Ollama is simpler for single-GPU rungs (0-1).

## The smart play
Climb the ladder, don't leap it. **Start at rung 1** (72B, ~$2-4/hr) — it already beats
old DeepSeek and proves the rented-Forge workflow end to end. Then jump to **rung 3-4**
(671B / ~1T Kimi K2) for a session when you want to *feel* frontier — ~$20-35 for an hour
of the biggest brains open weights offer. Every rung is the same 3 commands; only the
node size and the bill change.
