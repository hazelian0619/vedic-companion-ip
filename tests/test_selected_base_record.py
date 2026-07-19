from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.record_selected_base import record_selected_base
from scripts.selected_hatch_run import resolve_selected_hatch_run
from scripts.select_identity_candidate import select_identity_candidate
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_hatch_ready(tmp_path: Path, *, completed: bool) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidate = {"candidate_id": "a"}
    candidates = session.write_public("safe-candidates.json", {"candidates": [candidate, {"candidate_id": "b"}, {"candidate_id": "c"}]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    boards = []
    for candidate_id in ("a", "b", "c"):
        directory = session.root / "candidates" / candidate_id
        directory.mkdir(parents=True)
        hero = directory / "identity-hero.png"
        board = directory / "identity-board.png"
        hero.write_bytes(f"hero-{candidate_id}".encode())
        board.write_bytes(f"board-{candidate_id}".encode())
        boards.append({"candidate_id": candidate_id, "hero": str(hero.relative_to(session.root)), "hero_sha256": _sha256(hero), "identity_board": str(board.relative_to(session.root)), "board_sha256": _sha256(board)})
    boards_manifest = session.write_public("identity-boards.json", {"boards": boards})
    session.transition("identity_boards_ready", artifact_paths=[boards_manifest], decision="rendered")
    select_identity_candidate(session.root, "a", decision="chosen")
    run_dir = session.root / "selected-hatch" / "a" / "hatch-pet-run"
    reference = run_dir / "references" / "reference-01.png"
    reference.parent.mkdir(parents=True)
    hero = session.root / "candidates" / "a" / "identity-hero.png"
    reference.write_bytes(hero.read_bytes())
    base = run_dir / "references" / "canonical-base.png"
    base.write_bytes(b"canonical-base")
    status = "complete" if completed else "pending"
    (run_dir / "imagegen-jobs.json").write_text(json.dumps({"jobs": [{"id": "base", "status": status, "input_images": [{"path": "references/reference-01.png", "role": "pet reference"}]}]}), encoding="utf-8")
    (run_dir / "pet_request.json").write_text('{"pet_id": "a"}', encoding="utf-8")
    run_manifest = session.write_public("selected-hatch-run.json", {"candidate_id": "a", "hero": str(hero.relative_to(session.root)), "hero_sha256": _sha256(hero), "identity_board": "candidates/a/identity-board.png", "board_sha256": _sha256(session.root / "candidates" / "a" / "identity-board.png"), "hatch_run_dir": str(run_dir.relative_to(session.root))})
    session.transition("selected_hatch_ready", artifact_paths=[run_manifest], decision="prepared")
    return session


def test_selected_base_record_locks_board_hero_and_completed_hatch_base(tmp_path: Path):
    session = _selected_hatch_ready(tmp_path, completed=True)

    lock = record_selected_base(session.root, reviewer="visual-qa", note="canonical base preserves the selected hero")

    payload = json.loads(lock.read_text(encoding="utf-8"))
    assert payload["candidate_id"] == "a"
    assert payload["hero_sha256"]
    assert payload["board_sha256"]
    assert payload["base_sha256"]
    assert payload["production_owner"] == "hatch-pet"
    assert json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"] == "base_accepted"


def test_selected_base_record_requires_a_completed_base_job(tmp_path: Path):
    session = _selected_hatch_ready(tmp_path, completed=False)

    with pytest.raises(ValueError, match="completed"):
        record_selected_base(session.root, reviewer="visual-qa", note="not ready")


def test_selected_hatch_run_resolves_the_new_identity_lock(tmp_path: Path):
    session = _selected_hatch_ready(tmp_path, completed=True)
    record_selected_base(session.root, reviewer="visual-qa", note="canonical base preserves the selected hero")

    handoff = resolve_selected_hatch_run(session.root)

    assert handoff["candidate_id"] == "a"
    assert handoff["identity_hero"].endswith("identity-hero.png")
    assert handoff["identity_board"].endswith("identity-board.png")
    assert handoff["canonical_base"].endswith("references/canonical-base.png")
