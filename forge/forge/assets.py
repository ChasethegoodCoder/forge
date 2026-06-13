"""
assets.py — generate game/app assets locally with Stable Diffusion (free, owned).

Same philosophy as the local LLM: the image model runs on YOUR 4070, no online service,
no limits, no per-image cost. Default is `sd-turbo` (1-4 steps, ~2 GB, fast) so it works
on your constrained VRAM; swap engine.image_model to an SDXL model for higher quality.

Optional: rembg makes a transparent PNG (real sprites need no background).

Setup (first use):
    pip install diffusers accelerate rembg
    # first run downloads the model (~2 GB for sd-turbo)
Use:
    python cli.py asset "a small red spike, pixel art, side view" spike.png --transparent
"""
from __future__ import annotations

from pathlib import Path

_PIPE = None  # cache the loaded pipeline (loading is the slow part)


def _pipe(model: str):
    global _PIPE
    if _PIPE is not None:
        return _PIPE
    import torch
    from diffusers import AutoPipelineForText2Image
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    p = AutoPipelineForText2Image.from_pretrained(model, torch_dtype=dtype)
    p = p.to("cuda" if torch.cuda.is_available() else "cpu")
    p.set_progress_bar_config(disable=True)
    _PIPE = p
    return p


def generate_image(prompt: str, out_path: str, model: str = "stabilityai/sd-turbo",
                   steps: int = 3, transparent: bool = False) -> str:
    """Generate one image to out_path. Returns the path or an error string."""
    try:
        pipe = _pipe(model)
    except Exception as e:
        return (f"ERROR loading image model: {e}\n"
                f"Install:  pip install diffusers accelerate")
    # sd-turbo wants guidance_scale=0; standard SD wants ~7. Auto-pick.
    turbo = "turbo" in model.lower()
    img = pipe(prompt=prompt, num_inference_steps=steps if turbo else max(steps, 20),
               guidance_scale=0.0 if turbo else 7.0).images[0]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if transparent:
        try:
            from rembg import remove
            img = remove(img)
            out = out.with_suffix(".png")
        except Exception:
            pass  # rembg optional; fall back to opaque
    img.save(out)
    return str(out)
