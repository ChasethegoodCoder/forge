"""
cli.py — Forge entry point.

    python cli.py chat                 # interactive agent REPL
    python cli.py solve "task..."      # one-shot agent run (shows steps)
    python cli.py bench                 # run the benchmark suite
    python cli.py report                # print progress over time
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from forge.agent import Agent
from forge.backend import get_backend


def cmd_chat(model: str | None):
    agent = Agent(get_backend(model))
    print("Forge agent ready. Type 'exit' to quit.\n")
    while True:
        try:
            task = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if task.lower() in {"exit", "quit"}:
            break
        if not task:
            continue
        res = agent.run(task)
        print(f"forge> {res.answer}\n  ({len(res.steps)} steps, stop={res.stopped_reason})\n")


def cmd_solve(task: str, model: str | None):
    agent = Agent(get_backend(model))
    res = agent.run(task)
    for i, s in enumerate(res.steps, 1):
        print(f"[{i}] {s.action}({s.args}) -> {s.observation[:120]!r}")
    print(f"\nANSWER: {res.answer}")


def main():
    args = sys.argv[1:]
    model = None
    if "--model" in args:
        i = args.index("--model")
        model = args[i + 1]
        del args[i:i + 2]

    if not args or args[0] == "chat":
        cmd_chat(model)
    elif args[0] == "solve":
        cmd_solve(" ".join(args[1:]), model)
    elif args[0] == "bench":
        from bench.harness import main as bench_main
        sys.argv = ["bench"] + (["--model", model] if model else [])
        bench_main()
    elif args[0] == "report":
        from bench.report import main as report_main
        report_main()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
