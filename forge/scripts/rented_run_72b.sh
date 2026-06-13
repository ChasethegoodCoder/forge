#!/usr/bin/env bash
# rented_run_72b.sh — ON A RENTED A100 80GB: serve Qwen2.5-72B and run Forge's
# HumanEval on it, so you WATCH a 72B beat your local 7B (and old DeepSeek) on your
# own scoreboard. One command. Run it from inside the cloned forge/ repo.
#
#   bash scripts/rented_run_72b.sh
#
# Costs ~$1.40/hr while the pod is ON. Total run ≈ 20-30 min (download + serve + bench).
# TERMINATE the pod when the score prints — that's how you stop paying.
set -euo pipefail

MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ"   # 4-bit, ~40GB — fits one 80GB A100
export HF_HUB_ENABLE_HF_TRANSFER=1

echo ">> [1/4] Installing vLLM + Forge deps (~2 min)..."
pip install -q vllm requests pyyaml

echo ">> [2/4] Serving $MODEL on localhost:8000 (downloads ~40GB first time)..."
vllm serve "$MODEL" --quantization awq --max-model-len 8192 \
  --gpu-memory-utilization 0.95 --host 0.0.0.0 --port 8000 >/tmp/vllm.log 2>&1 &
VLLM_PID=$!

echo ">> [3/4] Waiting for the server (download can take 10-15 min)..."
for i in $(seq 1 120); do
  if curl -fsS http://localhost:8000/v1/models >/dev/null 2>&1; then echo "   ready."; break; fi
  sleep 15
  if ! kill -0 $VLLM_PID 2>/dev/null; then echo "vLLM died — see /tmp/vllm.log"; tail -20 /tmp/vllm.log; exit 1; fi
done

echo ">> [4/4] Pointing Forge at it and running HumanEval (raw, 40 problems)..."
export FORGE_BACKEND=openai   # not read directly; we set config below
python - <<'PY'
import pathlib, yaml
p = pathlib.Path("config/forge.yaml")
cfg = yaml.safe_load(p.read_text())
cfg["engine"]["backend"] = "openai"
cfg["engine"]["host"] = "http://localhost:8000"
cfg["engine"]["model"] = "Qwen/Qwen2.5-72B-Instruct-AWQ"
p.write_text(yaml.safe_dump(cfg))
print("config -> 72B via vLLM")
PY

python -m bench.humaneval --limit 40 --mode raw

echo ""
echo "================================================================"
echo " That pass@1 is your 72B's score. Compare to your 7B (~80-90%)"
echo " and to old DeepSeek-Coder-V2 (~80% HumanEval). Bigger brain, your bench."
echo " >>> TERMINATE THE POD NOW so you stop paying. <<<"
echo "================================================================"
kill $VLLM_PID 2>/dev/null || true
