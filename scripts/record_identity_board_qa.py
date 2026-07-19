#!/usr/bin/env python3
"""Record an explicit visual QA verdict for one rendered Identity Board."""
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
        raise ValueError("Identity Board artifact is missing or outside the session")
    return path


def record_identity_board_qa(
    session_root: Path,
    candidate_id: str,
    *,
    reviewer: str,
    note: str,
    identity_consistent: bool,
    art_direction_distinct: bool,
    typography_acceptable: bool,
    board_complete: bool,
) -> Path:
    session = ProductSession.create(Path(session_root))
    if _load(session.root / "session.json").get("state") != "candidates_ready":
        raise ValueError("Identity Board QA requires a candidates_ready session")
    render_path = session.root / "candidates" / candidate_id / "identity-render.json"
    if not render_path.is_file():
        raise ValueError("Identity Board render manifest is missing")
    render = _load(render_path)
    if render.get("candidate_id") != candidate_id:
        raise ValueError("Identity Board render does not match candidate")
    hero = _within(session, str(render.get("hero", "")))
    board = _within(session, str(render.get("identity_board", "")))
    if render.get("hero_sha256") != _sha256(hero) or render.get("board_sha256") != _sha256(board):
        raise ValueError("Identity Board render hashes do not match its artifacts")
    normalized_reviewer = " ".join(reviewer.split())
    normalized_note = " ".join(note.split())
    if not normalized_reviewer or not normalized_note:
        raise ValueError("Identity Board QA requires reviewer and note")
    qa = session.write_public(
        f"candidates/{candidate_id}/identity-board-qa.json",
        {
            "candidate_id": candidate_id,
            "hero_sha256": _sha256(hero),
            "board_sha256": _sha256(board),
            "identity_consistent": bool(identity_consistent),
            "art_direction_distinct": bool(art_direction_distinct),
            "typography_acceptable": bool(typography_acceptable),
            "board_complete": bool(board_complete),
            "reviewer": normalized_reviewer,
            "note": normalized_note,
        },
    )
    return qa


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--identity-consistent", action="store_true")
    parser.add_argument("--art-direction-distinct", action="store_true")
    parser.add_argument("--typography-acceptable", action="store_true")
    parser.add_argument("--board-complete", action="store_true")
    args = parser.parse_args()
    try:
        print(
            record_identity_board_qa(
                args.session_dir,
                args.candidate_id,
                reviewer=args.reviewer,
                note=args.note,
                identity_consistent=args.identity_consistent,
                art_direction_distinct=args.art_direction_distinct,
                typography_acceptable=args.typography_acceptable,
                board_complete=args.board_complete,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
