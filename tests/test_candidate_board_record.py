from __future__ import annotations

import json
import hashlib
from pathlib import Path

from scripts.record_candidate_boards import record_candidate_boards
from session_contract import ProductSession


def _bases_ready_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public(
        "safe-candidates.json",
        {"candidates": [{"candidate_id": value} for value in ("a", "b", "c")]},
    )
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    runs = session.write_public("candidate-runs/candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="prepared")
    bases = []
    for candidate_id in ("a", "b", "c"):
        base = session.root / "candidate-runs" / candidate_id / "hatch-pet-run" / "references" / "canonical-base.png"
        base.parent.mkdir(parents=True)
        base.write_bytes(f"base-{candidate_id}".encode())
        bases.append({"candidate_id": candidate_id, "canonical_base": str(base.relative_to(session.root))})
    bases_manifest = session.write_public("candidate-bases.json", {"bases": bases})
    session.transition("candidate_bases_ready", artifact_paths=[bases_manifest], decision="accepted")
    return session


def _qa(session: ProductSession, candidate_id: str, board: Path) -> Path:
    base = session.root / "candidate-runs" / candidate_id / "hatch-pet-run" / "references" / "canonical-base.png"
    qa = session.root / "candidates" / candidate_id / "character-bible-qa.json"
    qa.write_text(
        json.dumps(
            {
                "ok": True,
                "candidate_id": candidate_id,
                "board_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
                "base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return qa


def test_record_candidate_boards_locks_all_three_matching_base_board_pairs(tmp_path: Path):
    session = _bases_ready_session(tmp_path)
    boards = {}
    qas = {}
    for candidate_id in ("a", "b", "c"):
        board = session.root / "candidates" / candidate_id / "character-bible.png"
        board.parent.mkdir(parents=True)
        board.write_bytes(f"board-{candidate_id}".encode())
        boards[candidate_id] = board
        qas[candidate_id] = _qa(session, candidate_id, board)

    result = record_candidate_boards(session.root, boards, qas, board_system="professional-editorial-v2")

    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["board_system"] == "professional-editorial-v2"
    assert [item["candidate_id"] for item in payload["boards"]] == ["a", "b", "c"]
    assert all(item["base_sha256"] and item["board_sha256"] for item in payload["boards"])
    assert all(item["board_qa_sha256"] for item in payload["boards"])
    assert json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"] == "candidate_boards_ready"


def test_record_candidate_boards_rejects_an_incomplete_candidate_set(tmp_path: Path):
    session = _bases_ready_session(tmp_path)
    board = session.root / "candidates" / "a" / "character-bible.png"
    board.parent.mkdir(parents=True)
    board.write_bytes(b"board-a")

    try:
        record_candidate_boards(session.root, {"a": board}, {}, board_system="professional-editorial-v2")
    except ValueError as error:
        assert "all candidates" in str(error)
    else:
        raise AssertionError("incomplete candidate boards must fail")


def test_record_candidate_boards_rejects_a_qa_file_that_does_not_match_its_board(tmp_path: Path):
    session = _bases_ready_session(tmp_path)
    boards = {}
    qas = {}
    for candidate_id in ("a", "b", "c"):
        board = session.root / "candidates" / candidate_id / "character-bible.png"
        board.parent.mkdir(parents=True)
        board.write_bytes(f"board-{candidate_id}".encode())
        boards[candidate_id] = board
        qas[candidate_id] = _qa(session, candidate_id, board)
    payload = json.loads(qas["b"].read_text(encoding="utf-8"))
    payload["board_sha256"] = "wrong"
    qas["b"].write_text(json.dumps(payload), encoding="utf-8")

    try:
        record_candidate_boards(session.root, boards, qas, board_system="professional-editorial-v2")
    except ValueError as error:
        assert "QA" in str(error)
    else:
        raise AssertionError("unmatched board QA must fail")
