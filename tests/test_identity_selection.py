from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.prepare_selected_hatch_run import prepare_selected_hatch_run
from scripts.select_identity_candidate import select_identity_candidate
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate(candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "ip_name": f"Pet {candidate_id}",
        "display_name": f"Pet / {candidate_id}",
        "form_metaphor": "a nested keepsake wrap",
        "body_grammar": "An asymmetric wrap-bodied companion with one oversized quilted shoulder flap and two offset soft feet.",
        "silhouette_tokens": ["comma-shaped wrap body", "offset soft feet"],
        "relationship_gesture": "It scoots close and turns its wrap flap outward like a tiny invitation.",
        "tactile_hook": "A pinchable plush edge and raised blanket stitching invite a calming thumb rub.",
        "palette_tokens": ["moss outer structure", "celadon face plane", "vermilion signal detail"],
        "material_tokens": ["matte ceramic outer shell", "woven fabric face surround", "brushed aluminum join"],
        "signature_hook": "one tucked fabric pull tab",
        "default_form_avoids": ["symmetric toy pod silhouette", "central status light or center button", "consumer electronics casing"],
        "anti_drift": ["no literal animal", "no generic blob", "no scenery"],
    }


def _identity_boards_ready(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": [_candidate("a"), _candidate("b"), _candidate("c")]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    boards = []
    for candidate_id in ("a", "b", "c"):
        directory = session.root / "candidates" / candidate_id
        directory.mkdir(parents=True)
        hero = directory / "identity-hero.png"
        board = directory / "identity-board.png"
        hero.write_bytes(f"hero-{candidate_id}".encode())
        board.write_bytes(f"board-{candidate_id}".encode())
        boards.append(
            {
                "candidate_id": candidate_id,
                "hero": str(hero.relative_to(session.root)),
                "hero_sha256": _sha256(hero),
                "identity_board": str(board.relative_to(session.root)),
                "board_sha256": _sha256(board),
            }
        )
    manifest = session.write_public("identity-boards.json", {"boards": boards})
    session.transition("identity_boards_ready", artifact_paths=[manifest], decision="rendered")
    return session


def test_identity_selection_locks_one_recorded_hero_and_board(tmp_path: Path):
    session = _identity_boards_ready(tmp_path)

    selection = select_identity_candidate(session.root, "a", decision="the user chose this companion")

    payload = json.loads(selection.read_text(encoding="utf-8"))
    assert payload["candidate_id"] == "a"
    assert payload["hero_sha256"]
    assert payload["board_sha256"]
    assert json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"] == "identity_selected"


def test_identity_selection_rejects_a_changed_hero(tmp_path: Path):
    session = _identity_boards_ready(tmp_path)
    (session.root / "candidates" / "a" / "identity-hero.png").write_bytes(b"changed")

    with pytest.raises(ValueError, match="hash"):
        select_identity_candidate(session.root, "a", decision="changed")


def test_selected_hatch_preparation_uses_only_the_locked_hero_reference(tmp_path: Path, monkeypatch):
    session = _identity_boards_ready(tmp_path)
    select_identity_candidate(session.root, "a", decision="chosen")
    helper = tmp_path / "hatch-pet" / "scripts" / "prepare_pet_run.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("", encoding="utf-8")
    captured: dict[str, list[str]] = {}

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **_kwargs):
        captured["command"] = command
        run_dir = Path(command[command.index("--output-dir") + 1])
        run_dir.mkdir(parents=True)
        (run_dir / "pet_request.json").write_text("{}", encoding="utf-8")
        (run_dir / "imagegen-jobs.json").write_text('{"jobs": []}', encoding="utf-8")
        return Result()

    monkeypatch.setattr("scripts.prepare_selected_hatch_run.subprocess.run", fake_run)

    run_manifest = prepare_selected_hatch_run(session.root, hatch_pet_dir=helper.parents[1])

    command = captured["command"]
    assert command.count("--reference") == 1
    assert command[command.index("--reference") + 1] == str(session.root / "candidates" / "a" / "identity-hero.png")
    assert json.loads(run_manifest.read_text(encoding="utf-8"))["candidate_id"] == "a"
    assert json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"] == "selected_hatch_ready"
