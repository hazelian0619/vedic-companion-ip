#!/usr/bin/env python3
"""Lock exactly one recorded Identity Board and hero before Hatch production."""
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
        raise ValueError("selected identity artifact is missing or outside the session")
    return path


def select_identity_candidate(session_root: Path, candidate_id: str, *, decision: str) -> Path:
    session = ProductSession.create(Path(session_root))
    if _load(session.root / "session.json").get("state") != "identity_boards_ready":
        raise ValueError("identity selection requires three accepted Identity Boards")
    candidate_ids = {str(item.get("candidate_id", "")) for item in _load(session.root / "safe-candidates.json").get("candidates", [])}
    if candidate_id not in candidate_ids:
        raise ValueError("candidate is not part of this session")
    record = next(
        (item for item in _load(session.root / "identity-boards.json").get("boards", []) if item.get("candidate_id") == candidate_id),
        None,
    )
    if not isinstance(record, dict):
        raise ValueError("candidate has no recorded Identity Board")
    hero = _within(session, str(record.get("hero", "")))
    board = _within(session, str(record.get("identity_board", "")))
    hero_hash = _sha256(hero)
    board_hash = _sha256(board)
    if record.get("hero_sha256") != hero_hash or record.get("board_sha256") != board_hash:
        raise ValueError("recorded Identity Board hero or board hash no longer matches")
    normalized_decision = " ".join(decision.split())
    if not normalized_decision:
        raise ValueError("identity selection requires a decision note")
    selection = session.write_public(
        "identity-selection.json",
        {
            "candidate_id": candidate_id,
            "hero": str(hero.relative_to(session.root)),
            "hero_sha256": hero_hash,
            "identity_board": str(board.relative_to(session.root)),
            "board_sha256": board_hash,
            "decision": normalized_decision,
        },
    )
    session.transition("identity_selected", artifact_paths=[selection], decision="user selected one hero-locked Identity Board")
    return selection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--decision", required=True)
    args = parser.parse_args()
    try:
        print(select_identity_candidate(args.session_dir, args.candidate_id, decision=args.decision))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
