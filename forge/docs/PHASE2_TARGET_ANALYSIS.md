# Phase 2 — Sonnet 4.6 Target Analysis

The target is not a mystery to reverse-engineer; it's a capability profile to
approximate. For each axis: **what it is, why it matters, how it drives advanced
performance.** The "Target" column is the score we're climbing toward (100 = the
target's level on our benchmark suite).

| Capability | Target | What it is | Why it matters / how it drives performance |
|---|---:|---|---|
| **Reasoning** | 100 | Multi-step inference, abstraction, holding constraints | The bottleneck for everything else. Strong reasoning lets the system plan, debug, and self-correct rather than pattern-match. |
| **Coding** | 100 | Correct, idiomatic, multi-file code that runs | Code is verifiable reasoning. High coding ⇒ the agent can build tools for itself, widening its own capability. |
| **Planning** | 100 | Decompose a goal into ordered, revisable steps | Turns a one-shot model into an agent. Good plans make long tasks tractable and recoverable. |
| **Writing** | 100 | Clear, well-structured, audience-tuned prose | The output layer. Even perfect reasoning fails the user if it's communicated poorly. |
| **Tool Use** | 100 | Pick the right tool, format args, read results | Tools are how a model affects the world and overcomes its own gaps (e.g. compute via code). |
| **Instruction Following** | 100 | Honor constraints, formats, and intent precisely | Reliability. A model that drifts from instructions can't be trusted in automation. |
| **Memory** | 100 | Recall relevant prior context by meaning | Enables continuity across a long task or many sessions; avoids re-deriving and repeating. |
| **Research** | 100 | Find, verify, and synthesize external info | Extends the model past its training cutoff and grounds claims in sources. |
| **Multi-Step Tasks** | 100 | Sustain coherence over many dependent actions | Where real work lives. Compounding small error rates kill long tasks unless each step is reliable. |
| **Self-Critique** | 100 | Detect and fix its own errors before finishing | The single biggest lever for a weak base model — catching mistakes recovers much of the raw-capability gap. |
| **Agent Behavior** | 100 | Autonomy, recovery, knowing when to stop/ask | The integration of all the above into dependable end-to-end task completion. |
| **Long-Context Understanding** | 100 | Use large inputs without losing the thread | Lets the system work over whole codebases/documents instead of fragments. |

## Strategic reading
The axes Forge can most cheaply close on its hardware are **Tool Use, Self-Critique,
Memory, Planning, and Research** — these are *harness* properties, not weight
properties. **Reasoning and Coding** have a hard floor set by the 7–14B base model;
we raise their *effective* score via verification loops and fine-tuning, but full
parity is the least likely axis to reach. The roadmap therefore front-loads
harness wins (fast, high ROI) and treats fine-tuning as a later, slower lever.
