#!/usr/bin/env python3
"""Record the three rendered Character Bibles before user selection."""
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


def _validated_qa(session: ProductSession, candidate_id: str, qa_path: Path, base: Path, board: Path) -> Path:
    qa = Path(qa_path).resolve()
    if not qa.is_file() or session.root not in qa.parents:
        raise ValueError("Character Bible QA is missing or outside the session")
    payload = _load(qa)
    if payload.get("ok") is not True or payload.get("candidate_id") != candidate_id:
        raise ValueError("Character Bible QA did not pass")
    if payload.get("base_sha256") != _sha256(base) or payload.get("board_sha256") != _sha256(board):
        raise ValueError("Character Bible QA does not match the canonical base and board")
    return qa


def record_candidate_boards(
    session_root: Path,
    boards_by_candidate: dict[str, Path],
    qa_by_candidate: dict[str, Path],
    *,
    board_system: str,
) -> Path:
    session = ProductSession.create(Path(session_root))
    manifest = _load(session.root / "session.json")
    if manifest["state"] != "candidate_bases_ready":
        raise ValueError("candidate boards require accepted canonical bases")
    candidate_ids = [item["candidate_id"] for item in _load(session.root / "safe-candidates.json").get("candidates", [])]
    if set(boards_by_candidate) != set(candidate_ids):
        raise ValueError("candidate boards must include all candidates exactly once")
    if set(qa_by_candidate) != set(candidate_ids):
        raise ValueError("candidate board QA must include all candidates exactly once")
    bases = {item["candidate_id"]: item["canonical_base"] for item in _load(session.root / "candidate-bases.json").get("bases", [])}
    if set(bases) != set(candidate_ids):
        raise ValueError("candidate base manifest must include all candidates exactly once")

    records = []
    for candidate_id in candidate_ids:
        base = (session.root / bases[candidate_id]).resolve()
        board = Path(boards_by_candidate[candidate_id]).resolve()
        for artifact in (base, board):
            if not artifact.is_file() or session.root not in artifact.parents:
                raise ValueError("candidate board or canonical base is missing or outside the session")
        qa = _validated_qa(session, candidate_id, qa_by_candidate[candidate_id], base, board)
        records.append(
            {
                "candidate_id": candidate_id,
                "canonical_base": str(base.relative_to(session.root)),
                "base_sha256": _sha256(base),
                "character_bible": str(board.relative_to(session.root)),
                "board_sha256": _sha256(board),
                "character_bible_qa": str(qa.relative_to(session.root)),
                "board_qa_sha256": _sha256(qa),
            }
        )
    boards_manifest = session.write_public("candidate-boards.json", {"board_system": board_system, "boards": records})
    session.transition("candidate_boards_ready", artifact_paths=[boards_manifest], decision="three canonical-base Character Bibles recorded")
    return boards_manifest


def _board_argument(value: str) -> tuple[str, Path]:
    candidate_id, separator, path = value.partition("=")
    if not separator or not candidate_id or not path:
        raise argparse.ArgumentTypeError("board entries must use candidate-id=/absolute/path/to/character-bible.png")
    return candidate_id, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--board", required=True, action="append", type=_board_argument)
    parser.add_argument("--qa", required=True, action="append", type=_board_argument)
    parser.add_argument("--board-system", default="professional-editorial-v3")
    args = parser.parse_args()
    try:
        print(record_candidate_boards(args.session_dir, dict(args.board), dict(args.qa), board_system=args.board_system))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
