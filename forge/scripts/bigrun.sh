#!/usr/bin/env bash
# bigrun.sh — run the HONEST benchmark suite on whatever model Forge is pointed at
# (your rented 72B / 671B / 1T). Run from inside forge/forge after pointing config at
# the served model. One command:  bash scripts/bigrun.sh
set -uo pipefail

LIM="${1:-164}"   # problems per benchmark (default: full HumanEval set — fixes flaw #3 noise)

echo ">> Installing common libs so correct solutions aren't failed by a missing package"
echo "   (fixes flaw #3: the scipy false-fail)..."
pip install -q numpy scipy pandas sympy networkx 2>/dev/null || true

echo "############ MBPP (standard, $LIM) ############"
python -m bench.mbpp --limit "$LIM" --mode raw || true

echo "############ HARD SUITE (LeetCode med/hard) ############"
python -m bench.harness --suite coding_hard || true

echo "############ HumanEval (for reference / saturated) ############"
python -m bench.humaneval --limit "$LIM" --mode raw || true

echo ""
echo ">> For the contamination-PROOF numbers, also run (need their pip packages):"
echo "   pip install evalplus && python -m bench.evalplus_gen --dataset humaneval --mode raw"
echo "   pip install bigcodebench && python -m bench.bigcodebench_gen --mode raw --limit 50"
echo "   python -m bench.livecodebench --after 2025-01-01 --mode agent --limit 30"
echo "   python -m bench.swebench --limit 5   (real GitHub issues)"
echo ""
echo ">>> Compare these to your local 7B (hard suite ~30%). Then TERMINATE the pod. <<<"
