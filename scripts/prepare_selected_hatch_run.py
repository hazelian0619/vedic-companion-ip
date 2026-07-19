#!/usr/bin/env python3
"""Prepare one official Hatch production run from a user-selected identity hero."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from candidate_handoff import build_hatch_handoff
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _within(session: ProductSession, relative_path: str) -> Path:
    path = (session.root / relative_path).resolve()
    if not path.is_file() or session.root not in path.parents:
        raise ValueError("selected identity artifact is missing or outside the session")
    return path


def _candidate(path: Path, candidate_id: str) -> dict:
    payload = _load(path)
    for candidate in payload.get("candidates", []):
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise ValueError(f"candidate not found: {candidate_id}")


def _selected_identity(session: ProductSession) -> tuple[dict, dict, Path, Path]:
    if _load(session.root / "session.json").get("state") != "identity_selected":
        raise ValueError("selected Hatch preparation requires an identity_selected session")
    selection = _load(session.root / "identity-selection.json")
    candidate_id = str(selection.get("candidate_id", ""))
    candidate = _candidate(session.root / "safe-candidates.json", candidate_id)
    record = next(
        (item for item in _load(session.root / "identity-boards.json").get("boards", []) if item.get("candidate_id") == candidate_id),
        None,
    )
    if not isinstance(record, dict):
        raise ValueError("selected candidate has no recorded Identity Board")
    hero = _within(session, str(selection.get("hero", "")))
    board = _within(session, str(selection.get("identity_board", "")))
    hero_hash = _sha256(hero)
    board_hash = _sha256(board)
    if (
        selection.get("hero_sha256") != hero_hash
        or selection.get("board_sha256") != board_hash
        or record.get("hero") != str(hero.relative_to(session.root))
        or record.get("identity_board") != str(board.relative_to(session.root))
        or record.get("hero_sha256") != hero_hash
        or record.get("board_sha256") != board_hash
    ):
        raise ValueError("selected Identity Board hashes do not match the locked artifacts")
    return candidate, selection, hero, board


def _prepare_hatch_run(
    candidate: dict,
    *,
    candidate_id: str,
    hero: Path,
    output_dir: Path,
    hatch_pet_dir: Path,
    force: bool,
) -> Path:
    helper = hatch_pet_dir / "scripts" / "prepare_pet_run.py"
    if not helper.is_file():
        raise ValueError(f"official hatch-pet helper not found: {helper}")
    handoff = build_hatch_handoff(candidate, candidate_id=candidate_id)
    command = [
        sys.executable,
        str(helper),
        "--pet-name", handoff["pet_name"],
        "--pet-id", handoff["pet_id"],
        "--display-name", handoff["display_name"],
        "--description", handoff["description"],
        "--pet-notes", handoff["pet_notes"],
        "--style-notes", handoff["style_notes"],
        "--style-preset", "auto",
        "--reference", str(hero),
        "--output-dir", str(output_dir),
    ]
    if force:
        command.append("--force")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "official hatch-pet preparation failed")
    if not (output_dir / "pet_request.json").is_file() or not (output_dir / "imagegen-jobs.json").is_file():
        raise RuntimeError("official hatch-pet preparation did not create a complete run")
    return output_dir.resolve()


def prepare_selected_hatch_run(session_root: Path, *, hatch_pet_dir: Path, force: bool = False) -> Path:
    """Scaffold one Hatch run with the selected hero as its sole reference image."""
    session = ProductSession.create(Path(session_root))
    candidate, selection, hero, board = _selected_identity(session)
    candidate_id = str(selection["candidate_id"])
    run_dir = session.root / "selected-hatch" / candidate_id / "hatch-pet-run"
    prepared = _prepare_hatch_run(
        candidate,
        candidate_id=candidate_id,
        hero=hero,
        output_dir=run_dir,
        hatch_pet_dir=Path(hatch_pet_dir),
        force=force,
    )
    if session.root not in prepared.parents:
        raise ValueError("official Hatch run must remain inside the product session")
    run_manifest = session.write_public(
        "selected-hatch-run.json",
        {
            "candidate_id": candidate_id,
            "hero": str(hero.relative_to(session.root)),
            "hero_sha256": _sha256(hero),
            "identity_board": str(board.relative_to(session.root)),
            "board_sha256": _sha256(board),
            "hatch_run_dir": str(prepared.relative_to(session.root)),
            "production_owner": "hatch-pet",
        },
    )
    session.transition("selected_hatch_ready", artifact_paths=[run_manifest], decision="one selected hero prepared for official Hatch production")
    return run_manifest


def prepare_legacy_selected_hatch_run(
    candidates_path: Path,
    candidate_id: str,
    identity_reference: Path,
    output_dir: Path,
    hatch_pet_dir: Path,
) -> Path:
    """Preserve the historical design-branch CLI for old sessions only."""
    reference = Path(identity_reference).resolve()
    if not reference.is_file():
        raise ValueError(f"identity reference missing: {reference}")
    prepared = _prepare_hatch_run(
        _candidate(candidates_path, candidate_id),
        candidate_id=candidate_id,
        hero=reference,
        output_dir=Path(output_dir),
        hatch_pet_dir=Path(hatch_pet_dir),
        force=False,
    )
    (prepared / "selection.json").write_text(
        json.dumps(
            {"candidate_id": candidate_id, "identity_reference": str(reference), "source": "legacy_imagev2_design_branch"},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return prepared


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--candidate-id")
    parser.add_argument("--identity-reference", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--hatch-pet-dir", type=Path, default=Path.home() / ".codex" / "skills" / "hatch-pet")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        if args.session_dir:
            if any(value is not None for value in (args.candidates, args.candidate_id, args.identity_reference, args.output_dir)):
                raise ValueError("session-based Hatch preparation does not accept legacy candidate or reference arguments")
            print(prepare_selected_hatch_run(args.session_dir, hatch_pet_dir=args.hatch_pet_dir, force=args.force))
        else:
            if not all((args.candidates, args.candidate_id, args.identity_reference, args.output_dir)):
                raise ValueError("legacy Hatch preparation requires --candidates --candidate-id --identity-reference and --output-dir")
            print(prepare_legacy_selected_hatch_run(args.candidates, args.candidate_id, args.identity_reference, args.output_dir, args.hatch_pet_dir))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
