from __future__ import annotations

import json
import hashlib
from pathlib import Path

from scripts.select_candidate import select_candidate
from session_contract import ProductSession


def ready_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a"}, {"candidate_id": "b"}, {"candidate_id": "c"}]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="prepared")
    base = session.root / "candidate-runs" / "a" / "hatch-pet-run" / "references" / "canonical-base.png"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"base-a")
    board = session.root / "candidates" / "a" / "character-bible.png"
    board.parent.mkdir(parents=True)
    board.write_bytes(b"board-a")
    bases = session.write_public("candidate-bases.json", {"bases": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root))}]})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="accepted")
    boards = session.write_public(
        "candidate-boards.json",
        {
            "boards": [
                {
                    "candidate_id": "a",
                    "canonical_base": str(base.relative_to(session.root)),
                    "base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
                    "character_bible": str(board.relative_to(session.root)),
                    "board_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
                }
            ]
        },
    )
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="rendered")
    return session


def test_selection_requires_one_existing_candidate_base_and_board(tmp_path: Path):
    session = ready_session(tmp_path)
    base = session.root / "candidate-runs" / "a" / "hatch-pet-run" / "references" / "canonical-base.png"
    board = session.root / "candidates" / "a" / "character-bible.png"

    selected = select_candidate(session.root, "a", base, board, decision="approved")

    record = json.loads(selected.read_text(encoding="utf-8"))
    assert record["candidate_id"] == "a"
    assert record["base_sha256"]
    assert record["board_sha256"]
    assert json.loads((session.root / "session.json").read_text())["state"] == "candidate_selected"


def test_selection_rejects_unknown_candidate(tmp_path: Path):
    session = ready_session(tmp_path)
    base = session.write_public("base.png", {})
    board = session.write_public("board.png", {})

    try:
        select_candidate(session.root, "missing", base, board, decision="approved")
    except ValueError as error:
        assert "candidate" in str(error)
    else:
        raise AssertionError("unknown candidate must fail")


def test_selection_rejects_existing_files_that_are_not_the_recorded_candidate_pair(tmp_path: Path):
    session = ready_session(tmp_path)
    base = session.write_public("candidates/a/other-base.png", {})
    board = session.write_public("candidates/a/other-board.png", {})

    try:
        select_candidate(session.root, "a", base, board, decision="approved")
    except ValueError as error:
        assert "recorded" in str(error)
    else:
        raise AssertionError("selection must use the recorded base and board pair")
