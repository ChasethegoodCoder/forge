"""Asset-generation tool — lets the agent create its own images while building a game."""
from __future__ import annotations

from . import tool
from .files import WORKSPACE


@tool(
    description=(
        "Generate an image asset (sprite, background, icon) locally with Stable Diffusion "
        "and save it into the project. Use this when a game/app needs art. Describe the "
        "asset clearly (style + subject + view). Set transparent=true for sprites."
    ),
    parameters={
        "prompt": {"type": "string", "description": "what to draw, e.g. 'pixel art red spike, side view'"},
        "path": {"type": "string", "description": "relative output path in workspace, e.g. 'assets/spike.png'"},
        "transparent": {"type": "boolean", "description": "true for a transparent-background sprite"},
    },
)
def generate_asset(prompt: str, path: str, transparent: bool = False) -> str:
    from ..assets import generate_image
    from ..config import get
    out = (WORKSPACE / path)
    out.parent.mkdir(parents=True, exist_ok=True)
    result = generate_image(prompt, str(out),
                            model=get("engine.image_model", "stabilityai/sd-turbo"),
                            transparent=transparent)
    return f"asset saved: {result}" if not result.startswith("ERROR") else result


@tool(
    description=(
        "Download an asset (image/font/sound/zip) from a URL into the project. Use for "
        "free game assets (e.g. Kenney.nl CC0 packs, OpenGameArt) when art is needed and "
        "code-drawn shapes won't do. Only use direct file URLs."
    ),
    parameters={
        "url": {"type": "string", "description": "direct URL to the file"},
        "path": {"type": "string", "description": "relative save path in workspace, e.g. 'assets/player.png'"},
    },
)
def download_asset(url: str, path: str) -> str:
    import requests
    from .files import _safe
    if not url.lower().startswith(("http://", "https://")):
        return "ERROR: url must start with http:// or https://"
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        out = _safe(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with out.open("wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                size += len(chunk)
                if size > 50_000_000:  # 50MB cap
                    break
        return f"downloaded {size} bytes -> {path}"
    except Exception as e:
        return f"ERROR downloading: {type(e).__name__}: {e}"
