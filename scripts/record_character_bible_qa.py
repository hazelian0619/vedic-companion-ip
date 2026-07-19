#!/usr/bin/env python3
"""Record visual acceptance for one Character Bible before candidate selection."""
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


def _base_for_candidate(session: ProductSession, candidate_id: str) -> Path:
    candidates = json.loads((session.root / "safe-candidates.json").read_text(encoding="utf-8")).get("candidates", [])
    if candidate_id not in {item.get("candidate_id") for item in candidates}:
        raise ValueError("candidate is not part of this session")
    bases = json.loads((session.root / "candidate-bases.json").read_text(encoding="utf-8")).get("bases", [])
    record = next((item for item in bases if item.get("candidate_id") == candidate_id), None)
    if not isinstance(record, dict):
        raise ValueError("candidate has no accepted canonical base")
    base = (session.root / str(record.get("canonical_base", ""))).resolve()
    if not base.is_file() or session.root not in base.parents:
        raise ValueError("candidate canonical base is missing or outside the session")
    return base


def record_character_bible_qa(
    session_root: Path,
    *,
    candidate_id: str,
    board: Path,
    reviewer: str,
    identity_consistent: bool,
    typography_acceptable: bool,
    layout_complete: bool,
    note: str,
) -> Path:
    session = ProductSession.create(Path(session_root))
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest.get("state") != "candidate_bases_ready":
        raise ValueError("Character Bible QA requires accepted canonical bases before candidate boards are recorded")
    base = _base_for_candidate(session, candidate_id)
    board = Path(board).resolve()
    if not board.is_file() or session.root not in board.parents:
        raise ValueError("Character Bible board is missing or outside the session")
    checks = {
        "identity_consistent": bool(identity_consistent),
        "typography_acceptable": bool(typography_acceptable),
        "layout_complete": bool(layout_complete),
    }
    return session.write_public(
        f"candidates/{candidate_id}/character-bible-qa.json",
        {
            "ok": all(checks.values()),
            "candidate_id": candidate_id,
            "character_bible": str(board.relative_to(session.root)),
            "board_sha256": _sha256(board),
            "canonical_base": str(base.relative_to(session.root)),
            "base_sha256": _sha256(base),
            "reviewer": _text(reviewer, "reviewer"),
            "note": _text(note, "note"),
            **checks,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--board", required=True, type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--identity-consistent", action="store_true")
    parser.add_argument("--typography-acceptable", action="store_true")
    parser.add_argument("--layout-complete", action="store_true")
    parser.add_argument("--note", required=True)
    args = parser.parse_args()
    try:
        print(
            record_character_bible_qa(
                args.session_dir,
                candidate_id=args.candidate_id,
                board=args.board,
                reviewer=args.reviewer,
                identity_consistent=args.identity_consistent,
                typography_acceptable=args.typography_acceptable,
                layout_complete=args.layout_complete,
                note=args.note,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
