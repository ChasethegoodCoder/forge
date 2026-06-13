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
