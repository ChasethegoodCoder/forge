# How to run a 500B+ model — step by step

The closest open models to "500B" are **Llama-3.1-405B** (405B) and **DeepSeek-V3/R1**
(671B MoE). This runbook uses **DeepSeek-V3 (671B)** — it's the strongest and, being MoE
(only ~37B active per token), the most efficient big one to run. Same steps work for
405B (smaller, cheaper).

## Honest cost first (read this)
A 671B model needs **~350 GB at 4-bit** → an **8×H100 node (640 GB)**. That rents at
**~$25–30/hr**. So:
- This is **not a $10 session** — budget **~$30–40** for one real hour (serve + benchmark).
- The 405B version fits the same 8×H100 and is a bit cheaper to run.
- Compared to your 72B (~$1.40/hr), this is the "feel the frontier" splurge, not daily use.

## Step by step (RunPod)

**1. Add credits.** Load ~$40 so a 1-hour session can't get cut off mid-run.

**2. Deploy the node.**
   - Pods → Deploy. **GPU: H100 SXM 80 GB.** **GPU count: 8** (use the 1–8 selector).
   - Template: **PyTorch 2.8** (same as before).
   - **Container disk: ~500 GB** (the 671B weights are ~350–400 GB). The node's big SSD
     handles this.
   - **Network volume:** for THIS rung, consider a ~400 GB volume — re-downloading 400 GB
     at $30/hr is costly, so paying ~$28/mo to keep it can be worth it IF you'll run it
     again soon. For a one-off, skip it and eat the download time.
   - Skip SSH key (use Web Terminal). Deploy.

**3. Connect** → Web Terminal (or Jupyter terminal).

**4. Get Forge + serve the model** (two commands, no symbols):
```
git clone https://github.com/ChasethegoodCoder/forge.git
cd forge/forge
```
Then serve across all 8 GPUs (the script handles tensor-parallelism):
```
bash scripts/provision_vllm.sh deepseek-ai/DeepSeek-V3 8
```
This installs vLLM and serves DeepSeek-V3 sharded over the 8 GPUs on port 8000.
(First run downloads ~400 GB — slow; watch /tmp for progress. Use 405B for less:
`bash scripts/provision_vllm.sh meta-llama/Llama-3.1-405B-Instruct 8`.)

**5. Point Forge at it.** In a SECOND terminal (keep vLLM running in the first):
```
cd forge/forge
python -c "import yaml,pathlib; p=pathlib.Path('config/forge.yaml'); c=yaml.safe_load(p.read_text()); c['engine'].update(backend='openai', host='http://localhost:8000', model='deepseek-ai/DeepSeek-V3'); p.write_text(yaml.safe_dump(c))"
python cli.py ping
```
`ping` confirms the 671B is reachable and answering.

**6. Benchmark it (the honest ones).**
```
bash scripts/bigrun.sh
```
Runs MBPP + hard suite + (optionally) the harder external benchmarks on the 671B.

**7. TERMINATE immediately.** Pods → your pod → **Terminate.** At ~$30/hr, every minute
is ~$0.50 — don't leave it idle.

## What you'll see
The 671B should crush your 7B's 30% on the hard suite and clearly beat the 72B — *this*
is where bigger models prove themselves (HumanEval can't show it). It still won't top
Sonnet 4.6 on SWE-bench, but you'll be running one of the biggest open brains on Earth,
inside the harness you built, for the price of a few coffees.

## The ladder beyond 500B
- **~1T:** `bash scripts/provision_vllm.sh moonshotai/Kimi-K2-Instruct 8` — same node,
  ~1T MoE.
- **2T+:** needs multiple nodes; open options thin, cost climbs fast.
- **Train one:** still impossible solo (datacenter, $tens of millions) — you rent and
  run, never build.
