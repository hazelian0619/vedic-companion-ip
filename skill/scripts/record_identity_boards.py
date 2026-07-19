#!/usr/bin/env python3
"""Record exactly three visually accepted Identity Boards before selection."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from session_contract import ProductSession


_QA_FIELDS = ("identity_consistent", "art_direction_distinct", "typography_acceptable", "board_complete")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _within(session: ProductSession, relative_path: str, *, label: str) -> Path:
    path = (session.root / relative_path).resolve()
    if not path.is_file() or session.root not in path.parents:
        raise ValueError(f"Identity Board {label} is missing or outside the session")
    return path


def _record(session: ProductSession, candidate_id: str) -> dict:
    directory = session.root / "candidates" / candidate_id
    render_path = directory / "identity-render.json"
    qa_path = directory / "identity-board-qa.json"
    if not render_path.is_file() or not qa_path.is_file():
        raise ValueError("Identity Boards must include all candidates with render and QA records")
    render = _load(render_path)
    qa = _load(qa_path)
    if render.get("candidate_id") != candidate_id or qa.get("candidate_id") != candidate_id:
        raise ValueError("Identity Board record does not match candidate")
    hero = _within(session, str(render.get("hero", "")), label="hero")
    board = _within(session, str(render.get("identity_board", "")), label="board")
    hero_hash = _sha256(hero)
    board_hash = _sha256(board)
    if render.get("hero_sha256") != hero_hash or render.get("board_sha256") != board_hash:
        raise ValueError("Identity Board render hashes do not match its artifacts")
    if qa.get("hero_sha256") != hero_hash or qa.get("board_sha256") != board_hash or not all(qa.get(field) is True for field in _QA_FIELDS):
        raise ValueError("Identity Board QA did not pass")
    return {
        "candidate_id": candidate_id,
        "hero": str(hero.relative_to(session.root)),
        "hero_sha256": hero_hash,
        "identity_board": str(board.relative_to(session.root)),
        "board_sha256": board_hash,
        "identity_board_qa": str(qa_path.relative_to(session.root)),
        "board_qa_sha256": _sha256(qa_path),
        "renderer": str(render.get("renderer", "")),
        "model": str(render.get("model", "")),
    }


def record_identity_boards(session_root: Path) -> Path:
    session = ProductSession.create(Path(session_root))
    if _load(session.root / "session.json").get("state") != "candidates_ready":
        raise ValueError("Identity Boards require a candidates_ready session")
    candidate_ids = [str(item.get("candidate_id", "")) for item in _load(session.root / "safe-candidates.json").get("candidates", [])]
    if len(candidate_ids) != 3 or len(set(candidate_ids)) != 3 or not all(candidate_ids):
        raise ValueError("Identity Boards require exactly three candidates")
    records = [_record(session, candidate_id) for candidate_id in candidate_ids]
    boards = session.write_public("identity-boards.json", {"board_kind": "identity-board-v1", "boards": records})
    session.transition("identity_boards_ready", artifact_paths=[boards], decision="three hero-locked Identity Boards recorded")
    return boards


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(record_identity_boards(args.session_dir))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
