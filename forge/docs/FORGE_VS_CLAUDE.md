# Forge vs. Claude Code (the thing you're talking to)

You asked: *what's the difference between you and this, and what features is it missing?*
Honest, concrete answer. "Claude Code" here = the assistant building Forge
(Claude Opus/Sonnet running inside an agent harness).

## The two gaps, kept separate
There are **two** different gaps, and conflating them is the classic mistake:

1. **The model gap (weights).** Claude is a frontier model (hundreds of billions of
   params, trained on vastly more compute). Forge's engine is Qwen2.5-7B — ~7B params
   on your 4070. This gap is **real and mostly permanent at this hardware tier.** No
   harness trick fully closes raw reasoning/world-knowledge.

2. **The harness gap (everything around the weights).** This is where Claude Code's
   power actually comes from — and it's **fully buildable by you.** Most items below
   are harness, not weights.

## Feature-by-feature: what Claude Code has that Forge doesn't (yet)

| Capability | Claude Code | Forge today | Gap type | On roadmap |
|---|---|---|:--:|:--:|
| Base model strength | Frontier (Opus/Sonnet) | Qwen2.5-7B local | **Weights** | partial (14B, QLoRA) |
| Long context | ~200K tokens, coherent | 8K, degrades | Weights+harness | P11 |
| Native tool/function calling | Robust, parallel calls | JSON protocol + json_mode | Harness | improving |
| Breadth of tools | Files, shell, web, browser, MCP, image, notebooks… | files, python, shell | **Harness** | P4 |
| Web search / research | Built-in, live | none yet | **Harness** | P4 |
| Subagents / parallel agents | Spawns specialized agents | single agent | **Harness** | P9 |
| Planning & todo tracking | Explicit plan + task state | implicit in loop | **Harness** | P9/P14 |
| Self-critique / review | Strong, built-in | verify-gate v0 only | **Harness** | P6 |
| Persistent + semantic memory | Project memory, recall by meaning | JSON key/value | **Harness** | P5 |
| Codebase-scale understanding | Reads/edits whole repos, multi-file | single-file tasks | Harness+weights | P15 |
| Diff/patch editing | Surgical multi-file patches | whole-file write | **Harness** | P4 |
| Permissions / safety model | Sandboxing, approval prompts | basic sandbox | **Harness** | P12 |
| Multimodal (images, PDFs) | Yes | text only | Weights+harness | later |
| Instruction following | Very high reliability | moderate (7B) | **Weights** | P8 fine-tune |
| Reliability over long tasks | High (low per-step error) | error compounds | Weights+harness | P6/P9 |
| Streaming UX, IDE/terminal integration | Yes | CLI only | Harness | optional |
| Knowledge cutoff / world knowledge | Large, recent | smaller (7B) | **Weights** | mitigate via web (P4) |

## The honest scorecard
- **~11 of the ~16 gaps above are HARNESS gaps** — buildable on your hardware, no
  frontier compute needed. Forge's roadmap already targets every one of them.
- **~5 are WEIGHTS gaps** (raw model strength, long context, multimodal, world
  knowledge, peak instruction-following). These we *narrow* via: a bigger local model
  (14B-Q4), QLoRA fine-tuning on your own data, web tools to inject fresh knowledge,
  and multi-agent verification to recover reliability — but we don't claim full parity.

## What this means strategically
Forge should **aggressively close the harness gap first** (tools, memory, planning,
critic, multi-agent) because that's where the cheap, large wins are — and on
*narrow, well-defined coding tasks* a strong harness around a 7B model can approach a
frontier model's end-to-end success rate. Then use fine-tuning to chip at the weights
gap on the specific domains you care about (coding).

The benchmark (now anchored on **HumanEval**, where Sonnet's score is known) is what
keeps us honest about which gap we're actually closing.
