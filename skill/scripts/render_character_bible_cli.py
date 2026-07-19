#!/usr/bin/env python3
"""Render a Character Bible from one Hatch canonical base through official imagegen CLI."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from candidate_handoff import build_board_input
from character_bible import build_render_request


IMAGE_GEN = Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"


def _candidate(path: Path, candidate_id: str) -> dict:
    for candidate in json.loads(path.read_text(encoding="utf-8")).get("candidates", []):
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found: {candidate_id}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_character_bible_cli(
    candidates_path: Path,
    candidate_id: str,
    official_base: Path,
    out_path: Path,
    *,
    api_key_env: str,
    image_base_url: Optional[str],
    board_system: str = "professional-editorial-v2",
) -> Path:
    if not IMAGE_GEN.is_file():
        raise RuntimeError(f"official imagegen CLI not found: {IMAGE_GEN}")
    key = os.environ.get(api_key_env)
    if not key:
        raise RuntimeError(f"image provider key is not configured in {api_key_env}")
    candidates_path = Path(candidates_path).resolve()
    official_base = Path(official_base).resolve()
    out_path = Path(out_path).resolve()
    if not candidates_path.is_file() or not official_base.is_file():
        raise ValueError("candidate manifest and official base must exist")
    board_input = build_board_input(
        _candidate(candidates_path, candidate_id),
        official_base_path=official_base,
        board_system=board_system,
    )
    request = build_render_request(board_input)
    if request["reference_paths"] != [str(official_base)]:
        raise ValueError("production Character Bible requires exactly one official base reference")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path = out_path.with_suffix(".prompt.md")
    prompt_path.write_text(request["prompt"], encoding="utf-8")
    environment = dict(os.environ)
    environment["OPENAI_API_KEY"] = key
    if image_base_url:
        environment["OPENAI_BASE_URL"] = image_base_url.rstrip("/")
    command = [
        sys.executable,
        str(IMAGE_GEN),
        "edit",
        "--model",
        "gpt-image-2",
        "--image",
        str(official_base),
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
    subprocess.run(command, env=environment, check=True)
    if not out_path.is_file():
        raise RuntimeError("official imagegen CLI finished without producing a Character Bible")
    out_path.with_suffix(".json").write_text(
        json.dumps(
            {
                "candidate_id": candidate_id,
                "board_system": board_system,
                "reference_paths": request["reference_paths"],
                "official_base_sha256": _sha256(official_base),
                "character_bible_sha256": _sha256(out_path),
                "renderer": "official-imagegen-cli-edit",
                "model": "gpt-image-2",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--official-base", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--image-base-url")
    parser.add_argument("--board-system", default="professional-editorial-v2")
    args = parser.parse_args()
    try:
        print(
            render_character_bible_cli(
                args.candidates,
                args.candidate_id,
                args.official_base,
                args.out,
                api_key_env=args.api_key_env,
                image_base_url=args.image_base_url,
                board_system=args.board_system,
            )
        )
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
