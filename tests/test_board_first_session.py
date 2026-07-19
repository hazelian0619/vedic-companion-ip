from __future__ import annotations

from pathlib import Path

import pytest

from session_contract import ProductSession


def _candidates_ready_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": []})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    return session


def test_board_first_session_requires_identity_board_before_selection(tmp_path: Path):
    session = _candidates_ready_session(tmp_path)

    with pytest.raises(ValueError, match="not allowed"):
        session.transition("identity_selected", artifact_paths=[], decision="too early")


def test_board_first_states_reach_base_acceptance_without_candidate_bases(tmp_path: Path):
    session = _candidates_ready_session(tmp_path)
    boards = session.write_public("identity-boards.json", {"boards": []})
    session.transition("identity_boards_ready", artifact_paths=[boards], decision="rendered")
    selection = session.write_public("identity-selection.json", {"candidate_id": "a"})
    session.transition("identity_selected", artifact_paths=[selection], decision="user chose")
    run = session.write_public("selected-hatch-run.json", {"candidate_id": "a"})
    session.transition("selected_hatch_ready", artifact_paths=[run], decision="prepared")
    lock = session.write_public("identity-lock.json", {"candidate_id": "a"})
    session.transition("base_accepted", artifact_paths=[lock], decision="accepted")

    assert (session.root / "session.json").read_text(encoding="utf-8").find('"state": "base_accepted"') >= 0
