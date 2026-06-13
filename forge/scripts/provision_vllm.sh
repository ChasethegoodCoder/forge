#!/usr/bin/env bash
# provision_vllm.sh — serve a BIG model on a rented multi-GPU node via vLLM.
# This is for the bigger rungs (70B / 236B / 671B / ~1T) that need tensor-parallelism
# across several GPUs. Run it ON the rented box.
#
#   bash provision_vllm.sh Qwen/Qwen2.5-72B-Instruct 1     # 1 GPU (70B)
#   bash provision_vllm.sh deepseek-ai/DeepSeek-V3 8       # 8 GPUs (671B)
#   bash provision_vllm.sh moonshotai/Kimi-K2-Instruct 8   # 8 GPUs (~1T MoE)
#
# Then on YOUR PC point Forge at it (note: openai backend + port 8000):
#   in config/forge.yaml:  engine.backend: openai
#   FORGE_HOST=http://<box-ip>:8000 FORGE_MODEL=<the model id> python cli.py ping
set -euo pipefail

MODEL="${1:?usage: provision_vllm.sh <hf-model-id> <num-gpus>}"
TP="${2:-1}"   # tensor-parallel size = number of GPUs

echo ">> Installing vLLM..."
pip install -q vllm
export HF_HUB_ENABLE_HF_TRANSFER=1

echo ">> Serving $MODEL across $TP GPU(s) on 0.0.0.0:8000 ..."
echo "   (first run downloads the weights — big models take a while; use a fast-disk node)"
# --quantization may be needed for the largest models to fit; e.g. add: --quantization fp8
vllm serve "$MODEL" \
  --tensor-parallel-size "$TP" \
  --host 0.0.0.0 --port 8000 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.92

# vLLM exposes an OpenAI-compatible API at http://<box>:8000/v1
# Forge's OpenAICompatBackend talks to exactly that. Stop the box when done — you pay
# per hour it's ON, and big nodes are the expensive ones.
