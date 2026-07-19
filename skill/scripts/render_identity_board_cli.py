#!/usr/bin/env python3
"""Render one non-canonical hero and its text-bearing Identity Board through imagegen."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from candidate_handoff import build_identity_board_input
from identity_board import build_identity_board_requests
from session_contract import ProductSession


IMAGE_GEN = Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate(session: ProductSession, candidate_id: str) -> dict:
    manifest = _load(session.root / "session.json")
    if manifest.get("state") != "candidates_ready":
        raise ValueError("Identity Board rendering requires a candidates_ready session")
    payload = _load(session.root / "safe-candidates.json")
    candidate = next((item for item in payload.get("candidates", []) if item.get("candidate_id") == candidate_id), None)
    if not isinstance(candidate, dict):
        raise ValueError("candidate is not part of this session")
    return candidate


def _candidate_paths(session: ProductSession, candidate_id: str) -> dict[str, Path]:
    directory = (session.root / "candidates" / candidate_id).resolve()
    if session.root not in directory.parents:
        raise ValueError("candidate output must remain inside the session")
    return {
        "directory": directory,
        "hero": directory / "identity-hero.png",
        "board": directory / "identity-board.png",
        "hero_prompt": directory / "identity-hero.prompt.md",
        "board_prompt": directory / "identity-board.prompt.md",
        "manifest": directory / "identity-render.json",
    }


def _image_command(subcommand: str, prompt_path: Path, out_path: Path, images: list[Path]) -> list[str]:
    command = [
        sys.executable,
        str(IMAGE_GEN),
        subcommand,
        "--model",
        "gpt-image-2",
        "--prompt-file",
        str(prompt_path),
        "--use-case",
        "stylized-concept",
        "--quality",
        "high",
        "--size",
        "1024x1024",
        "--out",
        str(out_path),
        "--no-augment",
    ]
    for image in images:
        command.extend(("--image", str(image)))
    return command


def _provider_http_image_request(
    *,
    image_base_url: str,
    key: str,
    prompt_path: Path,
    out_path: Path,
    images: list[Path],
) -> None:
    """Use the same GPT Image model when a compatible provider cannot serve SDK edits."""
    endpoint = image_base_url.rstrip("/") + ("/images/edits" if images else "/images/generations")
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt_path.read_text(encoding="utf-8"),
        "size": "1024x1024",
        "quality": "high",
        "output_format": "png",
    }
    if images:
        _provider_http_edit_with_curl(endpoint=endpoint, key=key, payload=payload, images=images, out_path=out_path)
        return
    try:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {key}"},
            timeout=180,
            json=payload,
            files=None,
        )
        response.raise_for_status()
        result = response.json()
    except (OSError, ValueError, requests.RequestException) as error:
        raise RuntimeError("compatible provider image request failed") from error
    _decode_provider_image(result, out_path)


def _provider_http_edit_with_curl(*, endpoint: str, key: str, payload: dict[str, str], images: list[Path], out_path: Path) -> None:
    """Send compatible-provider edit multipart with credentials held only on stdin."""
    with tempfile.TemporaryDirectory(prefix="vedic-image-edit-") as temporary:
        response_path = Path(temporary) / "response.json"
        command = [
            "curl",
            "--silent",
            "--show-error",
            "--fail-with-body",
            "--max-time",
            "180",
            "--output",
            str(response_path),
            "--header",
            "@-",
        ]
        for key_name, value in payload.items():
            command.extend(("-F", f"{key_name}={value}"))
        for image in images:
            media_type = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
            command.extend(("-F", f"image=@{image};type={media_type}"))
        command.append(endpoint)
        result = subprocess.run(
            command,
            input=f"Authorization: Bearer {key}\n",
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode or not response_path.is_file():
            raise RuntimeError("compatible provider image edit request failed")
        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("compatible provider returned an invalid image edit response") from error
    _decode_provider_image(response, out_path)


def _decode_provider_image(result: object, out_path: Path) -> None:
    records = result.get("data") if isinstance(result, dict) else None
    encoded = records[0].get("b64_json") if isinstance(records, list) and records and isinstance(records[0], dict) else None
    if not isinstance(encoded, str) or not encoded:
        raise RuntimeError("compatible provider did not return a base64 image")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise RuntimeError("compatible provider returned invalid base64 image data") from error
    if not image_bytes:
        raise RuntimeError("compatible provider returned an empty image")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)


def render_identity_board_cli(
    session_root: Path,
    candidate_id: str,
    *,
    api_key_env: str,
    image_base_url: Optional[str],
    design_reference_path: str | Path = "",
    provider_http_fallback: bool = False,
) -> dict[str, Path]:
    """Create the hero first, then bind one board to that exact hero."""
    session = ProductSession.create(Path(session_root))
    candidate = _candidate(session, candidate_id)
    if not provider_http_fallback and not IMAGE_GEN.is_file():
        raise RuntimeError(f"official imagegen CLI not found: {IMAGE_GEN}")
    key = os.environ.get(api_key_env)
    if not key:
        raise RuntimeError(f"image provider key is not configured in {api_key_env}")
    if provider_http_fallback and not image_base_url:
        raise ValueError("provider HTTP fallback requires an explicit image base URL")
    design_reference = Path(design_reference_path).resolve() if str(design_reference_path).strip() else None
    if design_reference and not design_reference.is_file():
        raise ValueError("design reference is missing")
    paths = _candidate_paths(session, candidate_id)
    if any(paths[name].exists() for name in ("hero", "board", "manifest")):
        raise ValueError("Identity Board artifacts already exist; start a new session to render a new branch")
    paths["directory"].mkdir(parents=True, exist_ok=True)
    identity_input = build_identity_board_input(candidate, design_reference_path=design_reference or "")
    requests = build_identity_board_requests(identity_input)
    paths["hero_prompt"].write_text(str(requests["hero_prompt"]), encoding="utf-8")
    paths["board_prompt"].write_text(str(requests["board_prompt"]), encoding="utf-8")
    environment = dict(os.environ)
    environment["OPENAI_API_KEY"] = key
    if image_base_url:
        environment["OPENAI_BASE_URL"] = image_base_url.rstrip("/")

    hero_images: list[Path] = []
    if provider_http_fallback:
        _provider_http_image_request(
            image_base_url=str(image_base_url), key=key, prompt_path=paths["hero_prompt"], out_path=paths["hero"], images=hero_images
        )
    else:
        hero_command = _image_command("edit" if hero_images else "generate", paths["hero_prompt"], paths["hero"], hero_images)
        subprocess.run(hero_command, env=environment, check=True)
    if not paths["hero"].is_file():
        raise RuntimeError("official imagegen CLI finished without producing an identity hero")

    board_images = [paths["hero"]] + ([design_reference] if design_reference else [])
    if provider_http_fallback:
        _provider_http_image_request(
            image_base_url=str(image_base_url), key=key, prompt_path=paths["board_prompt"], out_path=paths["board"], images=board_images
        )
    else:
        board_command = _image_command("edit", paths["board_prompt"], paths["board"], board_images)
        subprocess.run(board_command, env=environment, check=True)
    if not paths["board"].is_file():
        raise RuntimeError("official imagegen CLI finished without producing an Identity Board")

    manifest = {
        "candidate_id": candidate_id,
        "hero": str(paths["hero"].relative_to(session.root)),
        "hero_sha256": _sha256(paths["hero"]),
        "identity_board": str(paths["board"].relative_to(session.root)),
        "board_sha256": _sha256(paths["board"]),
        "hero_prompt": str(paths["hero_prompt"].relative_to(session.root)),
        "board_prompt": str(paths["board_prompt"].relative_to(session.root)),
        "design_reference_path": str(design_reference) if design_reference else "",
        "renderer": "provider-http-imagegen-fallback" if provider_http_fallback else "official-imagegen-cli",
        "model": "gpt-image-2",
        "provider_http_fallback": provider_http_fallback,
    }
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {key: value for key, value in paths.items() if key != "directory"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--image-base-url")
    parser.add_argument("--design-reference", type=Path)
    parser.add_argument("--provider-http-fallback", action="store_true")
    args = parser.parse_args()
    try:
        rendered = render_identity_board_cli(
            args.session_dir,
            args.candidate_id,
            api_key_env=args.api_key_env,
            image_base_url=args.image_base_url,
            design_reference_path=args.design_reference or "",
            provider_http_fallback=args.provider_http_fallback,
        )
        print(json.dumps({key: str(value) for key, value in rendered.items()}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
