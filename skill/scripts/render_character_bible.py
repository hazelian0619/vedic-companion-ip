#!/usr/bin/env python3
"""Render one complete text-bearing Character Bible from safe visual inputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from candidate_handoff import build_board_input
from character_bible import build_render_request
from imagev2 import generate


def _candidate(path: Path, candidate_id: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found: {candidate_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--official-base", required=True, type=Path)
    parser.add_argument("--board-reference", type=Path)
    parser.add_argument("--board-system", default="collectible-editorial-v1")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        for path in (args.official_base,):
            if not path.is_file():
                raise ValueError(f"reference image missing: {path}")
        candidate = _candidate(args.candidates, args.candidate_id)
        board_input = build_board_input(
            candidate,
            official_base_path=args.official_base,
            board_reference_path=args.board_reference or "",
            board_system=args.board_system,
        )
        request = build_render_request(board_input)
        generate(request["prompt"], args.out, refs=[Path(path) for path in request["reference_paths"]])
        print(args.out)
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
