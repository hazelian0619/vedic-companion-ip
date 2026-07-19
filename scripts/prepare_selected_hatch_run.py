#!/usr/bin/env python3
"""Create a fresh official hatch run from a selected imagev2 design branch."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from candidate_handoff import build_hatch_handoff


def _candidate(path: Path, candidate_id: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for candidate in payload.get("candidates", []):
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found: {candidate_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--identity-reference", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--hatch-pet-dir", type=Path, default=Path.home() / ".codex" / "skills" / "hatch-pet")
    args = parser.parse_args()

    try:
        if not args.identity_reference.is_file():
            raise ValueError(f"identity reference missing: {args.identity_reference}")
        helper = args.hatch_pet_dir / "scripts" / "prepare_pet_run.py"
        if not helper.is_file():
            raise ValueError(f"official hatch-pet helper not found: {helper}")
        handoff = build_hatch_handoff(_candidate(args.candidates, args.candidate_id), candidate_id=args.candidate_id)
        command = [
            sys.executable,
            str(helper),
            "--pet-name", handoff["pet_name"],
            "--pet-id", handoff["pet_id"],
            "--display-name", handoff["display_name"],
            "--description", handoff["description"],
            "--pet-notes", handoff["pet_notes"],
            "--style-notes", handoff["style_notes"],
            "--reference", str(args.identity_reference),
            "--output-dir", str(args.output_dir),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "official hatch-pet preparation failed")
        (args.output_dir / "selection.json").write_text(
            json.dumps(
                {
                    "candidate_id": args.candidate_id,
                    "identity_reference": str(args.identity_reference.resolve()),
                    "source": "imagev2_design_branch",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(args.output_dir)
        return 0
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
