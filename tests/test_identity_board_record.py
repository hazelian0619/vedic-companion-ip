from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.record_identity_board_qa import record_identity_board_qa
from scripts.record_identity_boards import record_identity_boards
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _session_with_three_renders(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidate_ids = ["a", "b", "c"]
    candidates = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": item, "display_name": item} for item in candidate_ids]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    for candidate_id in candidate_ids:
        directory = session.root / "candidates" / candidate_id
        directory.mkdir(parents=True)
        hero = directory / "identity-hero.png"
        board = directory / "identity-board.png"
        hero.write_bytes(f"hero-{candidate_id}".encode())
        board.write_bytes(f"board-{candidate_id}".encode())
        (directory / "identity-render.json").write_text(
            json.dumps(
                {
                    "candidate_id": candidate_id,
                    "hero": str(hero.relative_to(session.root)),
                    "hero_sha256": _sha256(hero),
                    "identity_board": str(board.relative_to(session.root)),
                    "board_sha256": _sha256(board),
                    "renderer": "official-imagegen-cli",
                    "model": "gpt-image-2",
                }
            ),
            encoding="utf-8",
        )
    return session


def test_identity_board_recorder_requires_every_render_and_passing_qa(tmp_path: Path):
    session = _session_with_three_renders(tmp_path)
    for candidate_id in ("a", "b", "c"):
        record_identity_board_qa(
            session.root,
            candidate_id,
            reviewer="visual-qa",
            note="hero and board describe the same character",
            identity_consistent=True,
            art_direction_distinct=True,
            typography_acceptable=True,
            board_complete=True,
        )

    manifest = record_identity_boards(session.root)

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert len(payload["boards"]) == 3
    assert payload["boards"][0]["hero_sha256"]
    assert payload["boards"][0]["board_sha256"]
    state = json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"]
    assert state == "identity_boards_ready"


def test_identity_board_recorder_rejects_an_incomplete_candidate_set(tmp_path: Path):
    session = _session_with_three_renders(tmp_path)
    (session.root / "candidates" / "c" / "identity-render.json").unlink()

    with pytest.raises(ValueError, match="all candidates"):
        record_identity_boards(session.root)
