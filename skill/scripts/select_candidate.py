#!/usr/bin/env python3
"""Record the only candidate/base/board pair allowed to enter animation."""
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


def _recorded_pair(session: ProductSession, candidate_id: str, base: Path, board: Path) -> None:
    records = json.loads((session.root / "candidate-boards.json").read_text(encoding="utf-8")).get("boards", [])
    record = next((item for item in records if item.get("candidate_id") == candidate_id), None)
    if not isinstance(record, dict):
        raise ValueError("selected candidate has no recorded base and board pair")
    if (
        record.get("canonical_base") != str(base.relative_to(session.root))
        or record.get("character_bible") != str(board.relative_to(session.root))
        or record.get("base_sha256") != _sha256(base)
        or record.get("board_sha256") != _sha256(board)
    ):
        raise ValueError("selected files do not match the recorded candidate pair")


def select_candidate(session_root: Path, candidate_id: str, base_path: Path, board_path: Path, *, decision: str) -> Path:
    session = ProductSession.create(Path(session_root))
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest["state"] != "candidate_boards_ready":
        raise ValueError("candidate selection requires accepted bases and rendered boards")
    candidates = json.loads((session.root / "safe-candidates.json").read_text(encoding="utf-8")).get("candidates", [])
    if candidate_id not in {item.get("candidate_id") for item in candidates}:
        raise ValueError("candidate is not part of this session")
    base = Path(base_path).resolve()
    board = Path(board_path).resolve()
    for artifact in (base, board):
        if not artifact.is_file() or session.root not in artifact.parents:
            raise ValueError("selected artifact is missing or outside the session")
    _recorded_pair(session, candidate_id, base, board)
    selection = session.write_public(
        "selection.json",
        {
            "candidate_id": candidate_id,
            "base_path": str(base.relative_to(session.root)),
            "base_sha256": _sha256(base),
            "board_path": str(board.relative_to(session.root)),
            "board_sha256": _sha256(board),
            "decision": " ".join(decision.split()),
        },
    )
    session.transition("candidate_selected", artifact_paths=[selection], decision="user selected candidate/base/board pair")
    return selection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--decision", required=True)
    args = parser.parse_args()
    try:
        print(select_candidate(args.session_dir, args.candidate_id, args.base, args.board, decision=args.decision))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
