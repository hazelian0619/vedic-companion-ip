#!/usr/bin/env python3
"""Append a public provenance correction for already-rendered Character Bibles."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: str, field: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must be non-empty")
    return normalized


def record_board_provenance(
    session_root: Path,
    *,
    rendered_board_system: str,
    current_runtime_board_system: str,
    reason: str,
) -> Path:
    session = ProductSession.create(Path(session_root))
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest.get("state") != "candidate_boards_ready":
        raise ValueError("board provenance can be corrected only after candidate boards are recorded")
    boards_manifest = session.root / "candidate-boards.json"
    if not boards_manifest.is_file():
        raise ValueError("candidate board manifest is missing")
    correction = session.write_public(
        "candidate-board-provenance.json",
        {
            "candidate_boards_sha256": _sha256(boards_manifest),
            "rendered_board_system": _text(rendered_board_system, "rendered_board_system"),
            "current_runtime_board_system": _text(current_runtime_board_system, "current_runtime_board_system"),
            "reason": _text(reason, "reason"),
        },
    )
    session.record_event(
        "board_provenance_correction",
        artifact_paths=[correction],
        decision="recorded Character Bible rendering provenance correction",
    )
    return correction


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--rendered-board-system", required=True)
    parser.add_argument("--current-runtime-board-system", default="professional-editorial-v2")
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        print(
            record_board_provenance(
                args.session_dir,
                rendered_board_system=args.rendered_board_system,
                current_runtime_board_system=args.current_runtime_board_system,
                reason=args.reason,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
