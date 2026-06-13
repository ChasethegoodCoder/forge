# "No way it's that good" — you're right. Here are the honest benchmarks.

The 72B's 92.5% on HumanEval is **real but misleading**. This doc explains why and lays
out the benchmarks that actually tell the truth, easiest→hardest.

## Why HumanEval lies to you (at this skill level)
1. **Saturated** — 164 tiny standalone functions. Every strong model scores 90%+. It
   can't separate a good 7B from a frontier model anymore.
2. **Contaminated** — public since 2021, so it's in the training data. Models partly
   **memorize** the answers. Inflated scores.
3. **Tiny sample** — 40 problems = ±5% noise; one fail was a missing package.

Rule of thumb: **if a benchmark is old and public, top models have seen it.** Trust it
less the higher the score.

## The benchmark ladder (easy/inflated → hard/honest)

| Benchmark | What it measures | Why harder/honester | Forge support |
|---|---|---|---|
| HumanEval | tiny functions | saturated, contaminated | ✅ `bench/humaneval.py` |
| **MBPP** | basic functions (different set) | second data point | ✅ `bench/mbpp.py` (new) |
| **Hard suite** | DP/graphs/design (LeetCode med-hard) | actually separates models | ✅ `bench/tasks/coding_hard.jsonl` (new) |
| **HumanEval+ / MBPP+** (EvalPlus) | SAME problems, ~80× more tests | catches subtle bugs HumanEval misses; scores drop 10-20 pts | `pip install evalplus` |
| **BigCodeBench** | real-library, complex tasks | realistic, much harder | dataset on HF |
| **LiveCodeBench** | contest problems, **time-stamped** | test on problems released AFTER the model's cutoff → **zero contamination** | dataset on HF |
| **SWE-bench (Lite)** | fix real GitHub issues | hardest, most realistic; frontier ~50-70%, small models single digits | ✅ `bench/swebench.py` (built) |

## What to actually run to know how good it is
- **Quick honest check:** HumanEval+ and MBPP+ (EvalPlus) — same effort, the extra tests
  expose memorized-but-buggy solutions. Run on the rented 72B; watch the score drop from
  92% toward its *real* level.
- **Contamination-proof:** LiveCodeBench — problems dated after the model's training
  cutoff can't be memorized. This is the number to trust.
- **The real world:** SWE-bench Lite — already built. This is where "great at coding"
  is actually decided, and where a 72B vs a 7B (and vs Sonnet 4.6) genuinely separates.

## The honest expectation
On HumanEval the 72B and your 7B look close (both ~80-92%) because the test is easy.
On the **hard suite, EvalPlus, LiveCodeBench, and SWE-bench**, the gap opens up — and
that's where you'll see both (a) how much the 72B really beats your 7B, and (b) how far
any of it still is from Sonnet 4.6 (which leads SWE-bench, not HumanEval). Always weight
the **harder, newer, contamination-resistant** benchmarks most.
