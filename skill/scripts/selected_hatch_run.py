#!/usr/bin/env python3
"""Resolve the only hash-locked official Hatch run allowed to animate."""
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


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _within(session: ProductSession, relative_path: str) -> Path:
    path = (session.root / relative_path).resolve()
    if not path.is_file() or session.root not in path.parents:
        raise ValueError("selected artifact is missing or outside the session")
    return path


def resolve_selected_hatch_run(session_root: Path) -> dict[str, str]:
    session = ProductSession.create(Path(session_root))
    state = str(_load(session.root / "session.json")["state"])
    if state not in {"candidate_selected", "base_accepted", "animation_ready", "package_validated", "installed"}:
        raise ValueError("official Hatch animation requires an explicit candidate selection")
    selection = _load(session.root / "selection.json")
    candidate_id = str(selection.get("candidate_id", ""))
    base = _within(session, str(selection.get("base_path", "")))
    board = _within(session, str(selection.get("board_path", "")))
    if _sha256(base) != selection.get("base_sha256") or _sha256(board) != selection.get("board_sha256"):
        raise ValueError("selected base or board hash no longer matches the locked selection")
    board_records = _load(session.root / "candidate-boards.json").get("boards", [])
    record = next((item for item in board_records if item.get("candidate_id") == candidate_id), None)
    if not isinstance(record, dict):
        raise ValueError("selected candidate has no recorded Character Bible")
    if str(record.get("canonical_base")) != str(base.relative_to(session.root)):
        raise ValueError("selected base does not match the candidate board record")
    if str(record.get("character_bible")) != str(board.relative_to(session.root)):
        raise ValueError("selected board does not match the candidate board record")
    if record.get("base_sha256") != selection.get("base_sha256") or record.get("board_sha256") != selection.get("board_sha256"):
        raise ValueError("candidate board record does not match the locked selection")
    if base.name != "canonical-base.png" or base.parent.name != "references":
        raise ValueError("selected base is not an official Hatch canonical base")
    run_dir = base.parent.parent
    if not (run_dir / "imagegen-jobs.json").is_file() or not (run_dir / "pet_request.json").is_file():
        raise ValueError("selected official Hatch run is incomplete")
    return {
        "candidate_id": candidate_id,
        "run_dir": str(run_dir),
        "canonical_base": str(base),
        "character_bible": str(board),
        "base_sha256": str(selection["base_sha256"]),
        "board_sha256": str(selection["board_sha256"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(resolve_selected_hatch_run(args.session_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
