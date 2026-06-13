#!/usr/bin/env bash
# serve72b_ollama.sh — reliable path: run Qwen2.5-72B via OLLAMA (not vLLM) and
# benchmark it. Ollama handles the quantization/serving robustly and is Forge's
# default backend, so there's no fragile flag-tuning. One command on the rented box:
#   bash scripts/serve72b_ollama.sh
set -uo pipefail

echo ">> [0/4] (last vLLM error, if any, for the record)"
grep -iE "error|cuda|memory|quant|assert|no module|capability" /tmp/vllm.log 2>/dev/null | tail -8 || true
pkill -f vllm 2>/dev/null || true

echo ">> [1/4] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo ">> [2/4] Starting Ollama server..."
nohup ollama serve >/tmp/ollama.log 2>&1 &
sleep 6

echo ">> [3/4] Pulling qwen2.5:72b (~47GB, 10-15 min the first time)..."
ollama pull qwen2.5:72b

echo ">> [4/4] Pointing Forge at it and running HumanEval (FULL 164 problems)..."
# install common libs so a correct scipy/numpy solution isn't falsely failed (flaw #3)
pip install -q requests pyyaml numpy scipy pandas sympy networkx
python - <<'PY'
import pathlib, yaml
p = pathlib.Path("config/forge.yaml")
c = yaml.safe_load(p.read_text())
c["engine"]["backend"] = "ollama"
c["engine"]["host"] = "http://localhost:11434"
c["engine"]["model"] = "qwen2.5:72b"
p.write_text(yaml.safe_dump(c))
print("config -> qwen2.5:72b via Ollama")
PY

python -m bench.humaneval --limit 164 --mode raw

echo ""
echo "================================================================"
echo " That pass@1 is your 72B. Compare to your 7B (~80-90%) and old"
echo " DeepSeek-Coder-V2 (~80%). >>> TERMINATE THE POD NOW to stop paying. <<<"
echo "================================================================"
