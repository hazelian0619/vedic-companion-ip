#!/usr/bin/env python3
"""Render an imagev2 design branch inside a prepared official hatch seed run."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from character_bible import build_design_branch_request
from imagev2 import generate


def _candidate(path: Path, candidate_id: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for candidate in payload.get("candidates", []):
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found: {candidate_id}")


def identity_seed(hatch_seed_run: Path) -> str:
    """Read the official run's identity contract, excluding sprite production rules."""
    request_path = hatch_seed_run / "pet_request.json"
    if not request_path.is_file():
        raise ValueError(f"required branch input missing: {request_path}")
    request = json.loads(request_path.read_text(encoding="utf-8"))
    fields = ("description", "pet_notes", "style_notes")
    values = [" ".join(str(request.get(field, "")).split()) for field in fields]
    seed = " ".join(value for value in values if value)
    if not seed:
        raise ValueError("official hatch seed contains no identity fields")
    return seed


def render_branch_outputs(request: dict, out_dir: Path, *, generate_fn=generate) -> tuple[Path, Path]:
    """Render a board, then derive its only hatch identity reference from it."""
    out_dir.mkdir(parents=True, exist_ok=True)
    board_path = out_dir / "branch-board.png"
    identity_path = out_dir / "branch-identity-reference.png"
    generate_fn(request["board_prompt"], board_path, refs=[Path(path) for path in request["reference_paths"]])
    # The identity reference must be a child of the approved board, never a sibling sample.
    generate_fn(request["identity_reference_prompt"], identity_path, refs=[board_path])
    return board_path, identity_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--hatch-seed-run", required=True, type=Path)
    parser.add_argument("--board-reference", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    try:
        for path in (args.hatch_seed_run / "pet_request.json", args.board_reference):
            if not path.is_file():
                raise ValueError(f"required branch input missing: {path}")
        candidate = _candidate(args.candidates, args.candidate_id)
        request = build_design_branch_request(
            {**candidate, "hatch_seed_prompt": identity_seed(args.hatch_seed_run), "board_reference_path": str(args.board_reference)}
        )
        render_branch_outputs(request, args.out_dir)
        (args.out_dir / "branch.json").write_text(
            json.dumps(
                {
                    "candidate_id": args.candidate_id,
                    "hatch_seed_run": str(args.hatch_seed_run.resolve()),
                    "board_reference": str(args.board_reference.resolve()),
                    "board": "branch-board.png",
                    "identity_reference": "branch-identity-reference.png",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(args.out_dir)
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
