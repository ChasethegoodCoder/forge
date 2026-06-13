# Renting GPUs to run big models — what, how many, where

You don't buy a datacenter; you rent it by the hour and point Forge at it. Here's
exactly what to rent for each model size, and the legit places to rent it.

## How much VRAM a model needs (4-bit, the practical quant)
Rule of thumb: **total VRAM ≈ model-weight-size × ~1.2** (weights + KV cache + overhead).

| Model | ~Weights (4-bit) | GPUs to RUN it | Rough $/hr |
|---|---|---|---|
| 7B (what you run now) | ~5 GB | your 4070, or 1× anything | — |
| **70B** (big jump, very capable) | ~40 GB | **1× A100 80GB** or 1× H100 | ~$1.5–4 |
| **Llama 405B** | ~200 GB | **4× A100/H100 80GB** (320 GB) | ~$8–16 |
| **DeepSeek 671B** (MoE) | ~340 GB | **8× H100 80GB** node (640 GB) | ~$16–32 |

The "8×H100 node" (640 GB total) is the **standard unit** for running a 500B–671B model.
For Llama-405B, 4× 80 GB cards. For a 70B, a **single** 80 GB card — that's the
cost-effective sweet spot and already a massive step up from 7B (~$2/hr).

## GPU types you'll see (pick by VRAM)
- **RTX 4090 (24 GB)** — cheapest; good for ≤34B. ~$0.35–0.70/hr.
- **A100 80 GB** — workhorse; one runs a 70B. ~$1.5–2.5/hr.
- **H100 80 GB** — faster A100; nodes of 8 run 671B. ~$2–4/hr.
- **H200 141 GB** — fewer cards for big models (4× H200 ≈ 564 GB). ~$3–5/hr.

## Legit places to rent (reputable, individual-friendly)
| Site | Best for | Notes |
|---|---|---|
| **RunPod** (runpod.io) | individuals, per-second billing | Easy, cheap, "Secure Cloud" (datacenter) + "Community Cloud" (cheaper). Great default. |
| **Lambda Labs** (lambdalabs.com) | clean on-demand A100/H100 | Reputable ML-focused host; simple. |
| **Vast.ai** (vast.ai) | cheapest, marketplace | Peer hosts — cheapest prices, variable reliability; pick high-rated hosts. |
| **Paperspace / DigitalOcean Gradient** | notebooks, beginners | Friendly UI. |
| **Modal** (modal.com) | serverless GPU, pay-per-call | Code-first; spins up on demand. |
| **CoreWeave / Crusoe / Hyperstack / TensorDock** | bigger/cheaper clusters | Newer but legit. |
| **AWS p5 / GCP A3 / Azure ND** | enterprise | Most expensive; only if you already use them. |

**For you specifically:** start with **RunPod** or **Lambda** — rent **1× A100 80 GB**,
run a **70B** model (vLLM or Ollama), and point Forge at it. ~$2/hr, a huge capability
jump, no commitment. Scale to a multi-GPU node only when you want 405B/671B.

## How to point Forge at a rented box (3 steps)
1. On the rented machine, serve the model — e.g. `ollama serve` + `ollama pull llama3.1:70b`,
   or vLLM: `vllm serve meta-llama/Llama-3.1-70B-Instruct`.
2. Expose the port (the provider gives you a public URL / SSH tunnel).
3. In `config/forge.yaml` set `engine.host: http://<that-url>:11434` and
   `engine.model: llama3.1:70b`. Done — the whole harness now runs on the rented GPU.

## Cost reality
- Experiment for an evening on a 70B: **a few dollars.**
- Run 671B for an hour: **~$20–30.**
- **Always stop the instance when done** — you pay by the hour it's *on*, not used.
- This is renting *hardware*, not an API — your data, your model, your control. It just
  isn't free, which is the one trade vs your local-only 7B.
