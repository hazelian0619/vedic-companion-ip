#!/usr/bin/env python3
"""Lock the completed selected Hatch base to its chosen Identity Board."""
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


def _within(session: ProductSession, relative_path: str, *, label: str) -> Path:
    path = (session.root / relative_path).resolve()
    if not path.is_file() or session.root not in path.parents:
        raise ValueError(f"selected {label} is missing or outside the session")
    return path


def _text(value: str, field: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized


def record_selected_base(session_root: Path, *, reviewer: str, note: str) -> Path:
    session = ProductSession.create(Path(session_root))
    if _load(session.root / "session.json").get("state") != "selected_hatch_ready":
        raise ValueError("selected base recording requires a selected_hatch_ready session")
    selection = _load(session.root / "identity-selection.json")
    run_record = _load(session.root / "selected-hatch-run.json")
    candidate_id = str(selection.get("candidate_id", ""))
    if run_record.get("candidate_id") != candidate_id:
        raise ValueError("selected Hatch run does not match the locked identity selection")
    identity_record = next(
        (item for item in _load(session.root / "identity-boards.json").get("boards", []) if item.get("candidate_id") == candidate_id),
        None,
    )
    if not isinstance(identity_record, dict):
        raise ValueError("selected candidate has no recorded Identity Board")
    hero = _within(session, str(selection.get("hero", "")), label="hero")
    board = _within(session, str(selection.get("identity_board", "")), label="Identity Board")
    hero_hash = _sha256(hero)
    board_hash = _sha256(board)
    if any(
        value != expected
        for value, expected in (
            (selection.get("hero_sha256"), hero_hash),
            (selection.get("board_sha256"), board_hash),
            (identity_record.get("hero_sha256"), hero_hash),
            (identity_record.get("board_sha256"), board_hash),
            (run_record.get("hero_sha256"), hero_hash),
            (run_record.get("board_sha256"), board_hash),
        )
    ):
        raise ValueError("selected hero or Identity Board hash no longer matches")
    run_dir = (session.root / str(run_record.get("hatch_run_dir", ""))).resolve()
    if not run_dir.is_dir() or session.root not in run_dir.parents:
        raise ValueError("selected Hatch run is missing or outside the session")
    jobs = _load(run_dir / "imagegen-jobs.json").get("jobs", [])
    base_job = next((job for job in jobs if isinstance(job, dict) and job.get("id") == "base"), None)
    if not isinstance(base_job, dict) or base_job.get("status") != "complete":
        raise ValueError("selected Hatch run does not have a completed canonical base job")
    inputs = base_job.get("input_images")
    if not isinstance(inputs, list) or len(inputs) != 1 or not isinstance(inputs[0], dict):
        raise ValueError("selected Hatch base must use only the locked hero reference")
    hatch_reference = (run_dir / str(inputs[0].get("path", ""))).resolve()
    if not hatch_reference.is_file() or run_dir not in hatch_reference.parents or _sha256(hatch_reference) != hero_hash:
        raise ValueError("selected Hatch reference does not match the locked hero")
    base = run_dir / "references" / "canonical-base.png"
    if not base.is_file():
        raise ValueError("selected Hatch canonical base is missing")
    lock = session.write_public(
        "identity-lock.json",
        {
            "candidate_id": candidate_id,
            "identity_hero": str(hero.relative_to(session.root)),
            "hero_sha256": hero_hash,
            "identity_board": str(board.relative_to(session.root)),
            "board_sha256": board_hash,
            "hatch_run_dir": str(run_dir.relative_to(session.root)),
            "hatch_reference": str(hatch_reference.relative_to(session.root)),
            "hatch_reference_sha256": _sha256(hatch_reference),
            "canonical_base": str(base.relative_to(session.root)),
            "base_sha256": _sha256(base),
            "production_owner": "hatch-pet",
            "reviewer": _text(reviewer, "reviewer"),
            "note": _text(note, "note"),
        },
    )
    session.transition("base_accepted", artifact_paths=[lock], decision="selected Hatch base accepted and identity locked")
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", required=True)
    args = parser.parse_args()
    try:
        print(record_selected_base(args.session_dir, reviewer=args.reviewer, note=args.note))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
