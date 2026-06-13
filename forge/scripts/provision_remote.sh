#!/usr/bin/env bash
# provision_remote.sh — run this ON a rented GPU box (Linux) to make it a Forge backend.
# It installs Ollama, serves it on all network interfaces, and pulls a model.
#
#   bash provision_remote.sh llama3.1:70b
#
# Then, on YOUR machine, connect Forge to it:
#   FORGE_HOST=http://<box-public-ip>:11434 FORGE_MODEL=llama3.1:70b python cli.py ping
set -euo pipefail

MODEL="${1:-llama3.1:70b}"

echo ">> Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo ">> Starting Ollama on 0.0.0.0:11434 (reachable from your machine)..."
export OLLAMA_HOST=0.0.0.0:11434
pkill ollama 2>/dev/null || true
nohup ollama serve > ollama.log 2>&1 &
sleep 6

echo ">> Pulling model: $MODEL (this is the per-session download unless you use a persistent volume)..."
ollama pull "$MODEL"

IP="$(curl -s ifconfig.me || echo '<box-ip>')"
cat <<EOF

================================================================
 DONE. $MODEL is serving on port 11434.
 On YOUR machine, point Forge at this box:

   FORGE_HOST=http://$IP:11434 FORGE_MODEL=$MODEL python cli.py ping

 If that says [OK], everything (agent, bench, tools) runs on this GPU.
 IMPORTANT: STOP/terminate this instance when done — you pay while it's ON.
================================================================
EOF
