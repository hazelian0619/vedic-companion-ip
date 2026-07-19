from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.install_selected_pet import install_selected_pet
from scripts.select_candidate import select_candidate
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ready_selected_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "session")
    candidates = session.write_public("safe-candidates.json", {"candidates": [{"candidate_id": "a"}]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="fixture")
    run = session.root / "candidate-runs" / "a" / "hatch-pet-run"
    (run / "references").mkdir(parents=True)
    base = run / "references" / "canonical-base.png"
    base.write_bytes(b"base")
    (run / "imagegen-jobs.json").write_text(json.dumps({"jobs": [{"id": "idle", "status": "complete", "output_path": "decoded/idle.png"}]}), encoding="utf-8")
    (run / "pet_request.json").write_text(json.dumps({"pet_id": "a", "display_name": "A", "description": "A compact companion."}), encoding="utf-8")
    runs = session.write_public("candidate-runs.json", {"candidates": []})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    bases = session.write_public("candidate-bases.json", {"bases": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root))}]})
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    board = session.root / "candidates" / "a" / "character-bible.png"
    board.parent.mkdir(parents=True)
    board.write_bytes(b"board")
    boards = session.write_public("candidate-boards.json", {"board_system": "professional-editorial-v2", "boards": [{"candidate_id": "a", "canonical_base": str(base.relative_to(session.root)), "base_sha256": _sha256(base), "character_bible": str(board.relative_to(session.root)), "board_sha256": _sha256(board)}]})
    session.transition("candidate_boards_ready", artifact_paths=[boards], decision="fixture")
    select_candidate(session.root, "a", base, board, decision="chosen")
    (run / "final").mkdir()
    (run / "qa" / "previews").mkdir(parents=True)
    (run / "final" / "spritesheet.webp").write_bytes(b"webp")
    (run / "final" / "validation.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (run / "qa" / "contact-sheet.png").write_bytes(b"png")
    (run / "qa" / "review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (run / "qa" / "visual-qa.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    for state in ("idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review"):
        (run / "qa" / "previews" / f"{state}.gif").write_bytes(b"gif")
    return session


def test_install_selected_pet_installs_only_a_fully_valid_selected_run(tmp_path: Path):
    session = _ready_selected_session(tmp_path)
    install_root = tmp_path / "pets"

    pet_dir = install_selected_pet(session.root, install_root=install_root)

    assert (pet_dir / "spritesheet.webp").read_bytes() == b"webp"
    assert json.loads((pet_dir / "pet.json").read_text(encoding="utf-8"))["id"] == "a"
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "installed"
    assert json.loads((session.root / "installation.json").read_text(encoding="utf-8"))["pet_id"] == "a"
