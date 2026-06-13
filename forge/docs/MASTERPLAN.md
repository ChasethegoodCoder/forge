# Masterplan — make Forge the best it can be

Goal: match Claude Code's *capabilities* (and add more), accepting the one hard limit —
**per-piece quality stays 7B-level** unless a bigger model is rented for hard steps.
Everything below is the **harness**, which is fully buildable and is 70% of what makes a
coding agent feel powerful. Mapped to exactly what you asked for.

Legend: ✅ have · 🔨 build · ⬆️ upgrade existing

---

## Phase A — Build real apps (the geometry-dash goal) 🔨 TOP PRIORITY
The thing you keep coming back to. Needs the builder to *master each file* then integrate.
- ⬆️ **Builder v2 — master-then-assemble.** For each file: write → run → read the error →
  fix → repeat until it actually works (not just "created"). Then a final **integration
  pass**: run the whole program, capture errors, fix the wiring across files.
- 🔨 **Self-debug loop.** Feed runtime errors back to the agent with the file + traceback;
  iterate up to N times per file. This is how a small model gets real programs working.
- 🔨 **Game scaffold skill** (see Phase C): a pygame template so it starts from a working
  game loop instead of a blank page — then fills in player/obstacles/collision.
- **Ceiling:** simple/medium games become real; a polished Geometry Dash still needs a
  bigger model for the trickiest pieces (smooth physics, tuning). Builder makes it *try
  and run*, not stub.

## Phase B — Real file & folder access + permissions 🔨
You asked for access to folders/files and "allowing."
- 🔨 **Permission system** (like my model): the agent proposes a file/shell action; you
  approve/deny (or pre-allow patterns). Safe access *outside* the sandbox.
- ⬆️ **Open a real project**: point Forge at any folder on your PC (not just workspace),
  with read/edit/run scoped to it after you allow it.
- ✅ Already have: read/write/edit/grep/glob/run_in_project (sandboxed) — Phase B unlocks
  them on your real folders.

## Phase C — Skills (reusable capabilities) 🔨
Like my skills — pre-built scaffolds the agent picks up so it doesn't start from zero.
- 🔨 **Skills registry**: `skills/` folder of templates + instructions (pygame-game,
  flask-web-app, cli-tool, data-script, react-page...). The planner picks a matching
  skill and starts from its working scaffold.
- This is the single biggest quality multiplier for a 7B: starting from a correct skeleton
  hides most of the hard parts.

## Phase D — Documents: create + search 🔨
You asked for document creating and searches.
- 🔨 **Doc creation tools**: write Markdown/PDF/DOCX/XLSX (reportlab/python-docx/openpyxl).
- 🔨 **Document search (RAG)**: ingest a folder of docs → embed → semantic search tool, so
  the agent can answer from your files. (Reuses the semantic-memory engine you have.)

## Phase E — Memory & conversation history ⬆️
You asked for conversation history.
- ⬆️ **Persistent conversation history**: every chat saved + semantically recalled, so
  Forge remembers past sessions and projects. (Wire chat.py into semantic_memory.)
- ⬆️ **Project memory**: per-folder notes the agent keeps and re-reads.

## Phase F — A UI 🔨
- 🔨 **Desktop chat UI** (PyQt — you already have it from the `iris` project) OR a small
  **local web UI**: chat box, mode badge ([chat]/[coding]/[building]), file tree, live
  output. Talk to Forge like an app, not a terminal.

## Phase G — Smarter brain use (within/ beyond 7B) ⬆️
- ⬆️ **Best-of-N + critic always-on** for hard steps (you have the pieces).
- 🔨 **Big-model escalation**: a step the 7B fails twice auto-routes to a rented model
  (when you've pointed Forge at one) — small model does the easy 90%, big model does the
  hard 10%. Best cost/quality.

## Phase H — Keep it honest ✅⬆️
- ✅ The benchmark suite (HumanEval/MBPP/hard/SWE-bench/LiveCodeBench) — every feature is
  kept only if it moves a number.
- The one permanent truth: **the billions buy per-piece quality.** The harness can match
  my *features*; raw output parity needs a bigger model. We close every gap we can and
  rent for the rest.

---

## Progress
- ✅ **Phase A** — Builder v2 (self-debug + integration) — built.
- ✅ **Phase B** — real folder access via `--project <path>` (tools scoped to your files) — built.
- ✅ **Phase C** — Skills + pygame scaffold (stub → near-complete game) — built.
- ⬜ Phase D (documents) · E (conversation history) · F (UI — you're designing) · G (escalation — needs a rented model).

## Build order (recommended)
1. **Phase A — Builder v2 + self-debug** (gets you running games).
2. **Phase C — Skills** (pygame scaffold → geometry dash starts from a working loop).
3. **Phase B — permissions + real folders** (use it on actual projects).
4. **Phase E — conversation history**, then **Phase F — UI** (make it feel like an app).
5. **Phase D — documents**, **Phase G — escalation** (power features).

Each phase is independent and benchmark-gated. Start at the top; ship one at a time.
