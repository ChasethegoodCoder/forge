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


COMMANDS = """Forge commands:
  chat [--project <dir>]        talk to Forge (chats + codes; works on a real folder)
  build "<task>"                build a multi-file project (asks if ambiguous)
  solve "<task>"                one-shot agent run, shows steps + saves a trace
  image <path> "<question>"     ask the vision model about an image
  asset "<prompt>" <out.png>    generate art locally (Stable Diffusion); --transparent
  bench | humaneval | report    run benchmarks / see progress
  ping                          check the engine (local or rented) is reachable
  inspect                       replay the last solve's step trace
  help                          this list

Flags: --model <name>  --project <dir>
Config: config/forge.yaml (model, vision_model, image_model, big_model for escalation)"""


def cmd_ping(model: str | None):
    """Verify the configured backend (local OR rented remote) is reachable and works."""
    import time
    import requests
    from forge.config import get
    from forge.backend import get_backend, GenConfig, Message

    host = get("engine.host")
    kind = get("engine.backend", "ollama")
    print(f"Backend host: {host}  ({kind})")
    print(f"Model:        {model or get('engine.model')}")
    try:
        # Ollama lists at /api/tags; vLLM (openai) lists at /v1/models
        url = f"{host.rstrip('/')}/v1/models" if kind in ("openai", "vllm") else f"{host.rstrip('/')}/api/tags"
        data = requests.get(url, timeout=10).json()
        items = data.get("models") or data.get("data") or []
        names = [m.get("name") or m.get("id") for m in items]
        print(f"Reachable [OK]  ({len(names)} models available: {', '.join(str(n) for n in names[:6])})")
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


def cmd_image(path: str, question: str, model: str | None):
    """Ask a VISION model about an image. Needs a vision model pulled (e.g. llava:7b).
    Usage: python cli.py image photo.png "what's in this picture?" """
    import base64
    from pathlib import Path
    from forge.backend import OllamaBackend, GenConfig, Message
    from forge.config import get

    p = Path(path).expanduser()
    if not p.exists():
        print(f"No such image: {p}")
        return
    vmodel = model or get("engine.vision_model", "llava:7b")
    b64 = base64.b64encode(p.read_bytes()).decode()
    print(f"[vision] {vmodel} looking at {p.name}...")
    be = OllamaBackend(model=vmodel, host=get("engine.host", "http://localhost:11434"))
    try:
        out = be.chat([Message("user", question, images=[b64])], GenConfig(max_tokens=600))
        print(f"\n{out.strip()}")
    except Exception as e:
        print(f"Error: {e}\n(Pull a vision model first:  ollama pull {vmodel})")


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
    # Phase B: --project <path> points Forge's file tools at a REAL folder on your PC
    # (read/edit/run scoped to it) instead of the sandbox. Set BEFORE tools load.
    if "--project" in args:
        import os
        i = args.index("--project")
        root = os.path.abspath(os.path.expanduser(args[i + 1]))
        del args[i:i + 2]
        os.environ["FORGE_WORKSPACE"] = root
        print(f"[project] Forge is working in: {root}")
        print("[project] it can read/edit/run files HERE — real files, real changes.\n")

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
    elif args[0] in ("help", "commands", "--help", "-h"):
        print(COMMANDS)
    elif args[0] == "ping":
        cmd_ping(model)
    elif args[0] == "image":
        cmd_image(args[1], " ".join(args[2:]) or "Describe this image.", model)
    elif args[0] == "asset":
        transparent = "--transparent" in args
        a = [x for x in args[1:] if x != "--transparent"]
        prompt, out = a[0], (a[1] if len(a) > 1 else "asset.png")
        from forge.assets import generate_image
        from forge.config import get
        print(f"[asset] generating '{prompt}' -> {out} ...")
        print(generate_image(prompt, out, model=get("engine.image_model", "stabilityai/sd-turbo"),
                             transparent=transparent))
    elif args[0] == "build":
        from forge.builder import ProjectBuilder
        from forge import clarify
        be = get_backend(model)
        task = " ".join(args[1:])
        q = clarify.ask(be, task)              # ask like I do, if ambiguous
        if q:
            choice = clarify.prompt_cli(q)
            if choice:
                task = f"{task} ({q['question']} -> {choice})"
        ProjectBuilder(be).build(task)
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
