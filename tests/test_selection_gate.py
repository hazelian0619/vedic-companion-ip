from __future__ import annotations

import json
from pathlib import Path

from scripts.select_candidate import select_candidate
from session_contract import ProductSession


def ready_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    candidates = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a"}, {"candidate_id": "b"}, {"candidate_id": "c"}]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="prepared")
    bases = session.write_public("candidate-bases.json", {"bases": []})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="accepted")
    boards = session.write_public("candidate-boards.json", {"boards": []})
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="rendered")
    return session


def test_selection_requires_one_existing_candidate_base_and_board(tmp_path: Path):
    session = ready_session(tmp_path)
    base = session.write_public("candidates/a/canonical-base.png", {"not": "a real png"})
    board = session.write_public("candidates/a/character-bible.png", {"not": "a real png"})

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
