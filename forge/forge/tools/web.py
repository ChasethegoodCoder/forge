"""
web.py — research tools (Phase 18). Free, no API key: DuckDuckGo HTML endpoint +
plain HTTP fetch. This unlocks the Research axis (was ~15/100) and lets the agent
inject fresh, correct knowledge at inference time instead of relying on the 7B's
limited/older weights — the cheapest way to narrow the *weights* gap.

Only dependency is `requests` (already required). HTML is parsed with light regex
to avoid adding bs4; good enough for titles/links/snippets and readable text.
"""
from __future__ import annotations

import html
import re

import requests

from . import tool

_UA = {"User-Agent": "Mozilla/5.0 (Forge research agent)"}
_TAG = re.compile(r"<[^>]+>")
_RESULT = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    r'.*?class="result__snippet"[^>]*>(.*?)</a>',
    re.DOTALL,
)


def _strip(s: str) -> str:
    return html.unescape(_TAG.sub("", s)).strip()


@tool(
    description=(
        "Web search via DuckDuckGo. Returns top results as 'N. title — url\\n   snippet'. "
        "Use to find current info, docs, or facts beyond the model's knowledge."
    ),
    parameters={
        "query": {"type": "string", "description": "the search query"},
        "max_results": {"type": "integer", "description": "how many results (default 5)"},
    },
)
def web_search(query: str, max_results: int = 5) -> str:
    try:
        r = requests.get("https://html.duckduckgo.com/html/",
                         params={"q": query}, headers=_UA, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        return f"ERROR: search failed: {e}"
    out = []
    for i, (url, title, snippet) in enumerate(_RESULT.findall(r.text)[:max_results], 1):
        # DDG wraps target in a redirect; pull the real url if present
        m = re.search(r"uddg=([^&]+)", url)
        if m:
            from urllib.parse import unquote
            url = unquote(m.group(1))
        out.append(f"{i}. {_strip(title)} — {url}\n   {_strip(snippet)[:200]}")
    return "\n".join(out) or "(no results)"


@tool(
    description=(
        "Fetch a web page and return its readable text (HTML stripped, truncated). "
        "Use after web_search to read a specific result."
    ),
    parameters={
        "url": {"type": "string", "description": "the URL to fetch"},
        "max_chars": {"type": "integer", "description": "max characters to return (default 3000)"},
    },
)
def web_fetch(url: str, max_chars: int = 3000) -> str:
    try:
        r = requests.get(url, headers=_UA, timeout=25)
        r.raise_for_status()
    except requests.RequestException as e:
        return f"ERROR: fetch failed: {e}"
    body = r.text
    body = re.sub(r"(?is)<(script|style|head|nav|footer).*?</\1>", " ", body)
    text = re.sub(r"\n{3,}", "\n\n", _strip(body))
    return text[:max_chars] or "(empty page)"
