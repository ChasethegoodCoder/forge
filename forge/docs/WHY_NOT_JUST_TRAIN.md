# Why you can't just keep training it to reach Sonnet 4.6

Simple terms. Five reasons, with everyday analogies.

## 1. The model's size is fixed — training doesn't grow the brain
A model has a set number of "knobs" (parameters). The 7B has 7 billion; Sonnet is
*far* bigger. **Training only turns the knobs it already has — it never adds more.**
Think of a small notebook: you can write neater and erase mistakes, but you can't add
pages. A 7B brain has a hard capacity limit no amount of training removes. Your GPU
decides how big a brain fits (12 GB → up to ~14B). Bigger brain = different (bigger)
model, not more training.

## 2. Fine-tuning teaches *skills and style*, not raw intelligence
QLoRA mostly teaches the model to **use what it already knows better** — follow a
format, lean into coding, stop making a specific mistake. It does **not** pour in giant
new knowledge or raise its core reasoning much. It's polishing a car, not building a
faster engine.

## 3. It can only learn from data as good as what you can give it
Our factory makes training data using **the same 7B model**. A student taught only by
itself can't become smarter than itself — you can't lift yourself by your own
bootstraps. To jump to frontier level you'd need a frontier-level *teacher* (better
data/labels). We deliberately use no API, so our ceiling is "as good as the best data
we can generate locally," not "as good as Sonnet."

## 4. More training eventually makes it WORSE, not better
Keep training on the same data and two bad things happen:
- **Memorizing** (overfitting): it parrots your examples instead of generalizing.
- **Forgetting** (catastrophic forgetting): learning your narrow task erases general
  ability it used to have.
So "just train more" hits a wall and then declines. That's exactly why we **eval-gate**:
keep a new version only if it actually scores higher on held-out tests; otherwise throw
it away.

## 5. Frontier models cost millions of dollars of compute
Sonnet-class models are trained on **thousands of GPUs for months** with enormous
curated datasets. One RTX 4070 can *fine-tune* a small model (adjust a few knobs
cheaply) but cannot *train* a giant one. It's the difference between tuning a car in
your garage and building a car factory.

## So what CAN you do? (the realistic win)
- **Get a bigger brain that still fits:** run 14B instead of 7B (Lever 1).
- **Specialize the brain you have:** fine-tune it to be *excellent at coding* — a tuned
  7B can beat a generic bigger model *on that one job*, even if it's worse everywhere else.
- **Spend more thinking time:** harness tricks (critic, multi-pass, tools) make a fixed
  brain act smarter on hard tasks.

**Bottom line:** training makes a small model a *specialist*, not a *frontier generalist*.
Forge's whole bet is to win at coding specifically — close that gap as far as the
hardware allows — and accept it won't match Sonnet at everything. That's not failure;
it's choosing a fight you can actually win.
