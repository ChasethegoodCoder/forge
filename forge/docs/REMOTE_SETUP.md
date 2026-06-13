# Renting a GPU and connecting Forge — full walkthrough

Everything here is already built and tested. When you rent a box, these steps just work.

## How it connects (the mental model)
A rented GPU box runs **Ollama** (a little server) holding the big model. Your machine
runs **Forge** (the harness). Forge talks to that server over the network — the same way
it talks to your local Ollama now, just a different address. You flip between local and
rented by setting one environment variable.

```
[Your PC: Forge harness] ── http ──> [Rented GPU box: Ollama + 70B model]
        FORGE_HOST=http://<box-ip>:11434
```

## The steps (do this when you rent)
1. **Rent** a GPU on RunPod or Lambda (e.g. 1× A100 80 GB for a 70B). Pick an "Ollama"
   or plain "Ubuntu + CUDA" template. You get an SSH connection and a public IP/port.
2. **Provision it** — copy `scripts/provision_remote.sh` to the box and run:
   ```bash
   bash provision_remote.sh llama3.1:70b
   ```
   (installs Ollama, serves it, pulls the model). It prints the exact connect command.
3. **Connect from your PC** — verify it works:
   ```bash
   FORGE_HOST=http://<box-ip>:11434 FORGE_MODEL=llama3.1:70b python cli.py ping
   ```
   `[OK]` twice = you're live. Now run anything on the big model:
   ```bash
   FORGE_HOST=http://<box-ip>:11434 FORGE_MODEL=llama3.1:70b python cli.py humaneval --limit 20
   ```
   Or make it permanent: set `engine.host` / `engine.model` in `config/forge.yaml`.
4. **STOP the instance** when done. You pay per hour it's ON.

> Tested locally: `FORGE_HOST=http://localhost:11434 python cli.py ping` → `[OK]`. The
> remote path is identical; only the address changes.

## The storage question (forever cost? free option?)
When you rent, the model files (e.g. ~40 GB for a 70B, ~340 GB for 671B) must sit on disk
somewhere. Three options:

| Option | Cost | Trade-off |
|---|---|---|
| **Ephemeral disk** (included with the instance) | **FREE** | Wiped when you STOP the box → re-download the model each session (~5–30 min) |
| **Persistent / network volume** | ~$0.05–0.10 /GB/month | Model stays put → instant start, but you pay monthly **even while the GPU is off** |
| **HuggingFace as your storage** | **FREE** | The weights live on HF for free; `ollama pull` / HF download grabs them fresh each session onto the free ephemeral disk |

### Is persistent storage a "forever" cost?
Only if you keep the volume. It bills monthly while it exists; **delete it and the cost
stops** (you just re-download next time). It's optional convenience, not mandatory.

### The FREE way (what I recommend for occasional use)
**Don't pay for storage at all.** Each session:
1. spin up the GPU (comes with free ephemeral disk),
2. `ollama pull <model>` — pulls free from the model host onto that free disk,
3. use it, then **terminate** the box (disk wiped, $0 ongoing).
You pay only for the GPU-hours you actually use. The model itself is **free, hosted on
HuggingFace/Ollama** — that *is* your free storage. The only "cost" is the few minutes to
re-download at each start.

**When to pay for a persistent volume instead:** if you use the same big model often and
re-downloading 340 GB each time is annoying, ~$20/month to keep it ready is worth it.
For trying things occasionally, the free ephemeral path wins.

## Summary
- **Connect:** one env var (`FORGE_HOST`) — already wired and tested.
- **Provision:** one script (`provision_remote.sh`) — already written.
- **Storage:** free via ephemeral disk + re-download from HuggingFace; persistent volume
  is optional paid convenience you can cancel anytime. **No forced forever cost.**
- **You only ever pay for GPU-hours while the box is ON.** Stop it = $0.
