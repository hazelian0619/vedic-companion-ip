"""imagev2.py — the RELIABLE image engine: OpenRouter gpt-5.4-image-2 with
reference-image (multimodal) support. This is the proven path (board-ref-A
reached 9/10 with base-ref + layout-ref conditioning). Restored after the
codex-exec hatch-pet image path proved flaky (sandbox network disabled +
non-deterministic built-in image_gen + imagegen gate).

Two modes:
  * text-only: prompt -> one image.
  * reference: prompt + one or more reference images -> a view/edit/board
    of the SAME character (the conditioning that breaks the text ceiling).

Privacy: the prompt is the de-identified polished_prompt / board prompt (no
chart/planet words). Reference images are design-safe pet/layout images.
The model never sees birth data, chart dumps, or private reports.
"""
from __future__ import annotations
import base64
import io
import os
from pathlib import Path
from typing import Optional, Union
import requests

DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("IMAGEN_MODEL", "openai/gpt-5.4-image-2")


def resolve_connection() -> tuple[str, str]:
    """Return an ephemeral image endpoint and key without persisting credentials."""
    endpoint = os.environ.get("IMAGEV2_ENDPOINT", DEFAULT_ENDPOINT)
    key = os.environ.get("IMAGEV2_API_KEY") or os.environ["OPENROUTER_API_KEY"]
    return endpoint, key


def _data_url(path: Path) -> str:
    return f"data:image/png;base64,{base64.b64encode(Path(path).read_bytes()).decode()}"


def _data_url_scaled(path: Path, maxdim: int = 1280) -> str:
    """Downscale a ref to keep multi-image requests small (avoids SSL EOF)."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((maxdim, maxdim))
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return f"data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}"


def generate(
    prompt: str,
    out_path: Union[str, Path],
    *,
    refs: Optional[list[Path]] = None,
    scale_refs: bool = True,
    model: str = MODEL,
    timeout: int = 600,
) -> Path:
    """Generate one image. If `refs` given, condition on those images
    (style/pet/layout references). Returns the output path."""
    if refs:
        content = [{"type": "text", "text": prompt}]
        for r in refs:
            url = _data_url_scaled(Path(r)) if scale_refs else _data_url(Path(r))
            content.append({"type": "image_url", "image_url": {"url": url}})
    else:
        content = prompt
    endpoint, key = resolve_connection()
    r = requests.post(endpoint, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
    }, json={"model": model, "messages": [{"role": "user", "content": content}]},
        timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"imagev2 HTTP {r.status_code}: {r.text[:300]}")
    j = r.json()
    imgs = j["choices"][0]["message"].get("images") or []
    if not imgs:
        raise RuntimeError(f"imagev2 no image: content={(j['choices'][0]['message'].get('content') or '')[:200]}")
    url = imgs[0]["image_url"]["url"]
    if not url.startswith("data:image"):
        raise RuntimeError(f"imagev2 unexpected url: {url[:80]}")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(url.split(",", 1)[1]))
    return out_path
