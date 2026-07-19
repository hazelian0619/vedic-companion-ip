from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.record_character_bible_qa import record_character_bible_qa
from session_contract import ProductSession


def test_character_bible_qa_requires_all_four_visual_acceptance_decisions(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidate = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a"}]})
    session.transition("candidates_ready", artifact_paths=[candidate], decision="fixture")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    base = session.root / "candidate-runs" / "a" / "hatch-pet-run" / "references" / "canonical-base.png"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"base")
    bases = session.write_public("candidate-bases.json", {"bases": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root))}]})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    board = session.root / "candidates" / "a" / "character-bible.png"
    board.parent.mkdir(parents=True)
    board.write_bytes(b"board")
    board.with_suffix(".json").write_text(
        json.dumps(
            {
                "candidate_id": "a",
                "board_system": "professional-editorial-v2",
                "reference_paths": [str(base)],
                "official_base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
                "character_bible_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
                "renderer": "official-imagegen-cli-edit",
            }
        ),
        encoding="utf-8",
    )

    artifact = record_character_bible_qa(
        session.root,
        candidate_id="a",
        board=board,
        reviewer="visual-agent",
        identity_consistent=True,
        typography_acceptable=True,
        layout_complete=True,
        note="all acceptance checks pass",
    )

    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["board_sha256"] == hashlib.sha256(board.read_bytes()).hexdigest()
    assert payload["base_sha256"] == hashlib.sha256(base.read_bytes()).hexdigest()


def test_character_bible_qa_rejects_a_board_without_matching_renderer_provenance(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidate = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a"}]})
    session.transition("candidates_ready", artifact_paths=[candidate], decision="fixture")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    base = session.root / "candidate-runs" / "a" / "hatch-pet-run" / "references" / "canonical-base.png"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"base")
    bases = session.write_public("candidate-bases.json", {"bases": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root))}]})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    board = session.root / "candidates" / "a" / "character-bible.png"
    board.parent.mkdir(parents=True)
    board.write_bytes(b"board")

    try:
        record_character_bible_qa(
            session.root,
            candidate_id="a",
            board=board,
            reviewer="visual-agent",
            identity_consistent=True,
            typography_acceptable=True,
            layout_complete=True,
            note="all acceptance checks pass",
        )
    except ValueError as error:
        assert "renderer provenance" in str(error)
    else:
        raise AssertionError("a board without matching renderer provenance must not enter selection")
