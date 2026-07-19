from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.selected_hatch_run import resolve_selected_hatch_run
from scripts.select_candidate import select_candidate
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a"}, {"candidate_id": "b"}, {"candidate_id": "c"}]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    runs = session.write_public("candidate-runs/candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="prepared")
    base = session.root / "candidate-runs" / "a" / "hatch-pet-run" / "references" / "canonical-base.png"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"canonical-a")
    run_dir = base.parent.parent
    (run_dir / "imagegen-jobs.json").write_text('{"jobs": []}', encoding="utf-8")
    (run_dir / "pet_request.json").write_text('{"pet_id": "a"}', encoding="utf-8")
    bases = session.write_public("candidate-bases.json", {"bases": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root))}, {"candidate_id": "b", "canonical_base": "candidate-runs/b/hatch-pet-run/references/canonical-base.png"}, {"candidate_id": "c", "canonical_base": "candidate-runs/c/hatch-pet-run/references/canonical-base.png"}]})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="accepted")
    board = session.root / "candidates" / "a" / "character-bible.png"
    board.parent.mkdir(parents=True)
    board.write_bytes(b"board-a")
    boards = session.write_public("candidate-boards.json", {"board_system": "professional-editorial-v2", "boards": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root)), "base_sha256": _sha256(base), "character_bible": str(board.relative_to(session.root)), "board_sha256": _sha256(board)}]})
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="rendered")
    select_candidate(session.root, "a", base, board, decision="chosen")
    return session


def test_selected_hatch_run_returns_only_the_hash_locked_official_run(tmp_path: Path):
    session = _selected_session(tmp_path)

    handoff = resolve_selected_hatch_run(session.root)

    assert handoff["candidate_id"] == "a"
    assert handoff["run_dir"] == str(session.root / "candidate-runs" / "a" / "hatch-pet-run")
    assert handoff["canonical_base"].endswith("references/canonical-base.png")
    assert handoff["base_sha256"]
    assert handoff["board_sha256"]
    assert str(session.root / "private") not in json.dumps(handoff)


def test_selected_hatch_run_refuses_a_base_changed_after_selection(tmp_path: Path):
    session = _selected_session(tmp_path)
    base = session.root / "candidate-runs" / "a" / "hatch-pet-run" / "references" / "canonical-base.png"
    base.write_bytes(b"tampered")

    try:
        resolve_selected_hatch_run(session.root)
    except ValueError as error:
        assert "hash" in str(error)
    else:
        raise AssertionError("a mutated base must not enter animation")
