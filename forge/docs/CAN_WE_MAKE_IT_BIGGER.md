# Can we add "knobs" / make the model bigger? (the real ML answer)

Yes — there are genuine ways to add parameters, and I oversimplified before. Here's the
honest, complete picture, including how to actually do each on your 4070.

## First, the correction to "fine-tuning only teaches style"
That was too strong. There's a spectrum:
- **Instruction fine-tuning (SFT/QLoRA)** — mostly teaches *style/skill/format*. Polishing.
- **Continued PRE-training** — train on a large raw corpus (e.g. millions of lines of
  code). This **does add real knowledge/capability**, not just style. It's a smaller
  version of how the model was built. Needs lots of data + compute, but it genuinely
  raises capability, not just manners.
- **Knowledge distillation** — train your small model to imitate a *bigger* model's
  outputs. This transfers real capability "downhill." Catch: you need a stronger teacher
  (we have none locally beyond ~14B, and no API by your rule).

So: capability CAN be added, not only style — it just costs data + compute.

## Ways to literally add parameters ("more knobs")
| Technique | What it does | On a 4070? |
|---|---|---|
| **Run a bigger pretrained model** | 14B → 32B → 72B already have more knobs | 14B easy (Q4), 32B with CPU offload (slow), 72B too big |
| **Depth up-scaling** (SOLAR-style) | Duplicate/stack layers → a bigger model, then continue-train | Possible for small models; the *training* is the cost |
| **Model merging** (mergekit) | Stack/merge layers from models into a larger "frankenmerge" | Runs locally; quality is hit-or-miss without retraining |
| **MoE upcycling** | Turn a dense model into Mixture-of-Experts (more total params, few active) | Doable; needs training to specialize experts |

## The catch nobody can skip
Adding knobs is the easy part. **Fresh knobs start dumb.** A bigger model with
random/duplicated weights isn't smarter until you *train those weights* on good data
with enough compute. And the bigger model needs **more VRAM just to run**. So:

> The bottleneck was never "can I add parameters." It's "can I make the new
> parameters useful" — which needs frontier-scale **data + compute**. That's the wall.

Adding knobs without the compute to train them = a bigger container that's still empty.

## What's actually worth doing on YOUR hardware (in order)
1. **Run 14B** (already downloaded) — real "more knobs," works today. Maybe 32B-Q3 with
   offload if you tolerate slowness.
2. **Continued pre-training on code** (light) — feed lots of high-quality code so the
   model gains real coding knowledge, not just style. This is the closest lever to
   "pour in intelligence" that's feasible locally.
3. **Distill from the 14B into the 7B** — make the small model mimic the bigger one;
   keeps speed, borrows some capability.
4. **Fine-tune (QLoRA)** for skill/format on top.
5. **Merge** experiments — cheap to try, measure on the benchmark, keep only if it wins.

## The honest ceiling (again, because it matters)
You can make it *bigger* and *smarter than it is* — 7B → 14B → tuned/distilled — and on
**coding specifically** close much of the gap. You cannot, on one 12 GB GPU, reach
Sonnet 4.6's general intelligence, because that required thousands of GPUs and data you
can't reproduce. "Bigger" is real and worth doing; "frontier" is a different budget.
Every step here is gated on the benchmark — we keep a change only if the number moves.
