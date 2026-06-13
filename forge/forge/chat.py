"""
chat.py — natural conversation layer (talks like a person, codes like an engineer).

The bare Agent only emits JSON tool-actions — perfect for coding, useless for chatting.
This wraps it: each message is ROUTED. Plain conversation gets a warm, natural reply
(no tools, full history). A coding/task request is handed to the full Agent (tools,
verification) and its result is presented conversationally. So Forge can hold a normal
conversation AND, the moment you ask it to build/fix/run something, switch into its
strong coding mode — without you flipping a mode by hand.
"""
from __future__ import annotations

import json
import re

from .agent import Agent
from .backend import Backend, GenConfig, Message

CHAT_SYS = """You are Forge — a friendly, sharp AI assistant who is especially strong at
coding. Talk naturally and conversationally, like a knowledgeable friend: warm, clear,
and concise. Use normal prose (not JSON). Have real opinions, ask a clarifying question
when useful, and don't pad. When the user wants code written, fixed, or run, you'll
handle that in coding mode — here, just talk."""

ROUTER_SYS = """Classify the user's latest message. Reply with ONLY a JSON object:
{"mode":"task"}  -> they want code written/fixed/run/debugged, a file/project changed,
                    or a multi-step technical job that needs tools.
{"mode":"chat"}  -> anything else: conversation, questions, explanations, opinions.
When unsure, prefer "chat"."""

# fast-path heuristics so obvious coding asks skip the router call
_TASK_HINT = re.compile(
    r"\b(write|implement|fix|debug|refactor|run|build|create|code|function|class|"
    r"script|program|compile|test|bug|error|stack ?trace|api)\b", re.I)


class Conversation:
    def __init__(self, backend: Backend, use_agent: bool = True, use_memory: bool = False,
                 remember: bool = True):
        self.backend = backend
        self.history: list[Message] = []
        self.agent = Agent(backend, use_memory=use_memory) if use_agent else None
        self.remember = remember        # Phase E: persist + recall across sessions
        self._mem = None

    def _memory(self):
        if self._mem is None:
            from .semantic_memory import SemanticMemory
            self._mem = SemanticMemory()
        return self._mem

    def _recall(self, msg: str) -> str:
        """Pull relevant snippets from PAST sessions (semantic), for continuity."""
        if not self.remember:
            return ""
        try:
            hits = self._memory().search(msg, k=2, min_score=0.45)
            return "\n".join(f"- {h['text'][:200]}" for h in hits)
        except Exception:
            return ""

    def _store(self, msg: str, reply: str) -> None:
        if not self.remember:
            return
        try:
            self._memory().add(f"User said: {msg[:200]}\nForge replied: {reply[:300]}",
                               kind="conversation")
        except Exception:
            pass

    def _route(self, msg: str) -> str:
        if self.agent is None:
            return "chat"
        if _TASK_HINT.search(msg):
            return "task"
        try:
            raw = self.backend.chat(
                [Message("system", ROUTER_SYS), Message("user", msg)],
                GenConfig(temperature=0.0, json_mode=True, max_tokens=16))
            return "task" if json.loads(raw).get("mode") == "task" else "chat"
        except Exception:
            return "chat"

    def _chat_reply(self, msg: str) -> str:
        sys = CHAT_SYS
        recalled = self._recall(msg)
        if recalled:
            sys += f"\n\nFrom earlier conversations (use if relevant):\n{recalled}"
        msgs = [Message("system", sys), *self.history[-10:], Message("user", msg)]
        return self.backend.chat(msgs, GenConfig(temperature=0.6, max_tokens=600)).strip()

    def send(self, msg: str) -> tuple[str, str]:
        """Return (reply, mode). mode is 'chat' or 'task'."""
        mode = self._route(msg)
        if mode == "task" and self.agent:
            res = self.agent.run(msg)
            reply = res.answer.strip()
            # a brief natural lead-in if the answer is bare code
            if reply.startswith("```") or reply.startswith("def ") or reply.startswith("import "):
                reply = "Here you go:\n\n" + reply
        else:
            reply = self._chat_reply(msg)
        self.history.append(Message("user", msg))
        self.history.append(Message("assistant", reply))
        self._store(msg, reply)        # Phase E: remember across sessions
        return reply, mode
