#!/usr/bin/env bash
# provision_train.sh — FINE-TUNE Forge's model on a rented GPU box.
#
# Why rent for this: QLoRA on the 7B needs ~6-8 GB free VRAM. A desktop GPU is mostly
# eaten by the OS/browser, so training the 7B locally fails. A rented A100 80 GB (~$2/hr)
# has all the room — you fine-tune the 7B (or 14B/32B) on your full dataset in well under
# an hour, then bring the tiny adapter back home.
#
# Steps:
#   1. Rent 1x A100 80GB (RunPod/Lambda), SSH in.
#   2. Copy this repo to the box:   scp -r forge/ user@box:~/   (or git clone your fork)
#   3. bash provision_train.sh [BASE_MODEL] [N_GENERATE] [EPOCHS]
#   4. scp the adapters/ folder back home when done. Stop the instance.
set -euo pipefail

BASE="${1:-Qwen/Qwen2.5-7B-Instruct}"
NGEN="${2:-300}"
EPOCHS="${3:-3}"

echo ">> Installing training deps..."
pip install -q torch transformers peft trl bitsandbytes accelerate datasets hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1

echo ">> (Optional) growing the dataset to ~$NGEN examples via the local model..."
# needs Ollama for generation; skip with NGEN=0 if you copied data/gold over already
if [ "$NGEN" != "0" ]; then
  curl -fsSL https://ollama.com/install.sh | sh || true
  (OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve >/dev/null 2>&1 &) ; sleep 5
  ollama pull qwen2.5:7b-instruct || true
  python -m forge.factory.generate --n "$NGEN" || true
  python -m forge.mine --suites coding agent || true
fi

echo ">> Preparing training data..."
python -m forge.train.prepare

echo ">> Fine-tuning ($BASE, $EPOCHS epochs) — the step that needed the bigger GPU..."
python -m forge.train.qlora --base-model "$BASE" --epochs "$EPOCHS"

echo ">> Eval-gate on held-out HumanEval (promote only if it WINS)..."
python -m forge.train.eval_gate --base "$BASE" --limit 40 --offset 120

cat <<EOF

================================================================
 DONE. Adapter is in ./adapters/  (~40 MB — scp it back home).
 If eval_gate said PROMOTE: convert adapter->GGUF, 'ollama create forge-v1',
 set engine.model in config/forge.yaml. You now own a fine-tuned model.
 STOP/terminate this instance now — you pay while it's ON.
================================================================
EOF
