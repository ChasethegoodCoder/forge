"""
cli.py — Forge entry point.

    python cli.py chat                 # interactive agent REPL
    python cli.py solve "task..."      # one-shot agent run (shows steps)
    python cli.py bench                 # run the homemade benchmark suite
    python cli.py humaneval --limit 20  # standard HumanEval vs Sonnet 4.6
    python cli.py report                # print progress over time
    python cli.py inspect               # replay the last solve's trace
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from forge.agent import Agent
from forge.backend import get_backend


def cmd_chat(model: str | None):
    from forge.chat import Conversation
    convo = Conversation(get_backend(model))
    print("Forge ready — talk to me normally; I switch to coding mode when you ask for code.")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            msg = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if msg.lower() in {"exit", "quit"}:
            break
        if not msg:
            continue
        reply, mode = convo.send(msg)
        tag = "[coding]" if mode == "task" else "[chat]"
        print(f"forge {tag}> {reply}\n")


def cmd_ping(model: str | None):
    """Verify the configured backend (local OR rented remote) is reachable and works."""
    import time
    import requests
    from forge.config import get
    from forge.backend import get_backend, GenConfig, Message

    host = get("engine.host")
    print(f"Backend host: {host}")
    print(f"Model:        {model or get('engine.model')}")
    try:
        tags = requests.get(f"{host.rstrip('/')}/api/tags", timeout=10).json()
        names = [m.get("name") for m in tags.get("models", [])]
        print(f"Reachable [OK]  ({len(names)} models available: {', '.join(names[:6])})")
    except Exception as e:
        print(f"NOT reachable [FAIL]  {type(e).__name__}: {e}")
        print("  - is the box on? is Ollama serving on that host:port? is the port exposed?")
        return
    try:
        t0 = time.time()
        out = get_backend(model).chat([Message("user", "Reply with the single word: ok")],
                                      GenConfig(max_tokens=8))
        print(f"Generation [OK]  ({time.time()-t0:.1f}s)  -> {out.strip()[:40]!r}")
        print("\nForge is ready to use this backend. Everything (tools, bench, agent) runs on it.")
    except Exception as e:
        print(f"Generation [FAIL]  {type(e).__name__}: {e}")


def cmd_solve(task: str, model: str | None):
    from forge import trace
    agent = Agent(get_backend(model))
    res = agent.run(task)
    for i, s in enumerate(res.steps, 1):
        print(f"[{i}] {s.action}({s.args}) -> {s.observation[:120]!r}")
    print(f"\nANSWER: {res.answer}")
    path = trace.save(task, res)
    print(f"\n(trace saved -> {path.name}; view with: python cli.py inspect)")


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
    elif args[0] == "humaneval":
        from bench.humaneval import main as he_main
        sys.argv = ["humaneval"] + args[1:] + (["--model", model] if model else [])
        he_main()
    elif args[0] == "report":
        from bench.report import main as report_main
        report_main()
    elif args[0] == "inspect":
        from forge import trace
        print(trace.render(trace.latest()))
    elif args[0] == "ping":
        cmd_ping(model)
    elif args[0] == "dashboard":
        from bench.dashboard import main as dash_main
        dash_main()
    elif args[0] == "suggest":
        from forge.suggest import main as suggest_main
        suggest_main()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
