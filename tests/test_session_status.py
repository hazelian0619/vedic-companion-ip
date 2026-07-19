from __future__ import annotations

import json
from pathlib import Path

from scripts.session_status import session_status
from session_contract import ProductSession


def test_session_status_exposes_only_public_selection_information(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public(
        "safe-candidates.json",
        {"candidates": [{"candidate_id": "a", "display_name": "A"}, {"candidate_id": "b", "display_name": "B"}, {"candidate_id": "c", "display_name": "C"}]},
    )
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    session.write_private("chart/input.json", {"birth_date": "secret"})

    result = session_status(session.root)

    assert result["state"] == "candidates_ready"
    assert result["next_action"] == "render_identity_boards"
    assert result["candidates"] == [{"candidate_id": "a", "display_name": "A"}, {"candidate_id": "b", "display_name": "B"}, {"candidate_id": "c", "display_name": "C"}]
    assert str(session.root / "private") not in json.dumps(result)


def test_session_status_exposes_board_choices_only_after_all_boards_are_ready(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a", "display_name": "A"}]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="fixture")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    bases = session.write_public("candidate-bases.json", {"bases": []})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    boards = session.write_public("candidate-boards.json", {"board_system": "professional-editorial-v2", "boards": [{"candidate_id": "a", "canonical_base": "candidate-runs/a/hatch-pet-run/references/canonical-base.png", "character_bible": "candidates/a/character-bible.png"}]})
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="fixture")

    result = session_status(session.root)

    assert result["next_action"] == "select_candidate"
    assert result["board_system"] == "professional-editorial-v2"
    assert result["boards"] == [{"candidate_id": "a", "canonical_base": "candidate-runs/a/hatch-pet-run/references/canonical-base.png", "character_bible": "candidates/a/character-bible.png"}]


def test_session_status_prefers_a_matching_public_board_provenance_correction(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": []})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="fixture")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    bases = session.write_public("candidate-bases.json", {"bases": []})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    boards = session.write_public("candidate-boards.json", {"board_system": "professional-editorial-v2", "boards": []})
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="fixture")
    session.write_public(
        "candidate-board-provenance.json",
        {
            "candidate_boards_sha256": __import__("hashlib").sha256(boards.read_bytes()).hexdigest(),
            "rendered_board_system": "collectible-editorial-v1",
            "current_runtime_board_system": "professional-editorial-v2",
            "reason": "fixture",
        },
    )

    result = session_status(session.root)

    assert result["rendered_board_system"] == "collectible-editorial-v1"
    assert result["current_runtime_board_system"] == "professional-editorial-v2"
