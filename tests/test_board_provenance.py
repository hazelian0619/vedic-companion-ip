from __future__ import annotations

import json
from pathlib import Path

from scripts.record_board_provenance import record_board_provenance
from session_contract import ProductSession


def test_board_provenance_records_historical_rendering_without_rewriting_session_state(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    boards = session.write_public("candidate-boards.json", {"board_system": "professional-editorial-v2", "boards": []})
    session.transition("candidates_ready", artifact_paths=[boards], decision="fixture")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    bases = session.write_public("candidate-bases.json", {"bases": []})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="fixture")

    result = record_board_provenance(
        session.root,
        rendered_board_system="collectible-editorial-v1",
        current_runtime_board_system="professional-editorial-v2",
        reason="existing boards predate the source-traceable system",
    )

    payload = json.loads(result.read_text(encoding="utf-8"))
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    assert payload["rendered_board_system"] == "collectible-editorial-v1"
    assert payload["current_runtime_board_system"] == "professional-editorial-v2"
    assert manifest["state"] == "candidate_boards_ready"
    assert manifest["events"][-1]["kind"] == "board_provenance_correction"
