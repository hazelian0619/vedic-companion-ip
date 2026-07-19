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
from session_contract import ProductSession


IMAGE_GEN = Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"


def _accepted_candidate_and_base(session: ProductSession, candidate_id: str) -> tuple[dict, Path]:
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest.get("state") != "candidate_bases_ready":
        raise ValueError("Character Bible rendering requires recorded canonical bases")
    for candidate in json.loads((session.root / "safe-candidates.json").read_text(encoding="utf-8")).get("candidates", []):
        if candidate.get("candidate_id") == candidate_id:
            break
    else:
        raise ValueError(f"candidate not found: {candidate_id}")
    for record in json.loads((session.root / "candidate-bases.json").read_text(encoding="utf-8")).get("bases", []):
        if record.get("candidate_id") != candidate_id:
            continue
        base = (session.root / str(record.get("canonical_base", ""))).resolve()
        if not base.is_file() or session.root not in base.parents:
            break
        if record.get("base_sha256") != _sha256(base):
            break
        return candidate, base
    raise ValueError("candidate does not have an accepted canonical base")


def _expected_board_path(session: ProductSession, candidate_id: str, out_path: Path) -> Path:
    expected = (session.root / "candidates" / candidate_id / "character-bible.png").resolve()
    out_path = Path(out_path).resolve()
    if out_path != expected:
        raise ValueError("Character Bible output must use its candidate session path")
    return out_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_character_bible_cli(
    session_root: Path,
    candidate_id: str,
    out_path: Path,
    *,
    api_key_env: str,
    image_base_url: Optional[str],
    board_system: str = "professional-editorial-v3",
) -> Path:
    session = ProductSession.create(Path(session_root))
    candidate, official_base = _accepted_candidate_and_base(session, candidate_id)
    out_path = _expected_board_path(session, candidate_id, out_path)
    if not IMAGE_GEN.is_file():
        raise RuntimeError(f"official imagegen CLI not found: {IMAGE_GEN}")
    key = os.environ.get(api_key_env)
    if not key:
        raise RuntimeError(f"image provider key is not configured in {api_key_env}")
    board_input = build_board_input(
        candidate,
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
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--image-base-url")
    parser.add_argument("--board-system", default="professional-editorial-v3")
    args = parser.parse_args()
    try:
        print(
            render_character_bible_cli(
                args.session_dir,
                args.candidate_id,
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
