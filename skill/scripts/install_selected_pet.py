#!/usr/bin/env python3
"""Install the only selected, fully verified Hatch pet into a Codex pet directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.selected_hatch_run import resolve_selected_hatch_run
from scripts.verify_delivery import verify_delivery
from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pet_metadata(run_dir: Path) -> dict[str, str]:
    payload = json.loads((run_dir / "pet_request.json").read_text(encoding="utf-8"))
    pet_id = str(payload.get("pet_id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", pet_id):
        raise ValueError("official Hatch pet_id is invalid")
    display_name = " ".join(str(payload.get("display_name", "")).split())
    description = " ".join(str(payload.get("description", "")).split())
    if not display_name or not description:
        raise ValueError("official Hatch pet metadata is incomplete")
    return {"pet_id": pet_id, "display_name": display_name, "description": description}


def _stage_install(run_dir: Path, target: Path, metadata: dict[str, str]) -> None:
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing Codex pet: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{metadata['pet_id']}-", dir=target.parent))
    try:
        shutil.copy2(run_dir / "final" / "spritesheet.webp", staging / "spritesheet.webp")
        (staging / "pet.json").write_text(
            json.dumps(
                {
                    "id": metadata["pet_id"],
                    "displayName": metadata["display_name"],
                    "description": metadata["description"],
                    "spritesheetPath": "spritesheet.webp",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def install_selected_pet(session_root: Path, *, install_root: Path | None = None) -> Path:
    session = ProductSession.create(Path(session_root))
    handoff = resolve_selected_hatch_run(session.root)
    run_dir = Path(handoff["run_dir"])
    verification = verify_delivery(run_dir)
    if not verification["ok"]:
        raise ValueError(f"selected Hatch run is not ready for installation: {', '.join(verification['missing'])}")
    metadata = _pet_metadata(run_dir)
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest["state"] in {"candidate_selected", "base_accepted"}:
        session.transition(
            "animation_ready",
            artifact_paths=[
                run_dir / "final" / "spritesheet.webp",
                run_dir / "final" / "validation.json",
                run_dir / "qa" / "contact-sheet.png",
                run_dir / "qa" / "review.json",
                run_dir / "qa" / "visual-qa.json",
            ],
            decision="selected Hatch animation passed deterministic and visual QA",
        )
    summary = session.write_public(
        str((run_dir / "qa" / "run-summary.json").relative_to(session.root)),
        {
            "ok": True,
            "candidate_id": handoff["candidate_id"],
            "base_sha256": handoff["base_sha256"],
            "board_sha256": handoff["board_sha256"],
            "spritesheet_sha256": _sha256(run_dir / "final" / "spritesheet.webp"),
            "visual_qa": "passed",
        },
    )
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest["state"] == "animation_ready":
        session.transition("package_validated", artifact_paths=[summary], decision="selected Hatch package validated")
    root = Path(install_root) if install_root is not None else Path.home() / ".codex" / "pets"
    target = root.resolve() / metadata["pet_id"]
    _stage_install(run_dir, target, metadata)
    verification = verify_delivery(run_dir, install_dir=target)
    if not verification["ok"]:
        raise RuntimeError("installed pet failed delivery verification")
    installation = session.write_public(
        "installation.json",
        {
            "pet_id": metadata["pet_id"],
            "candidate_id": handoff["candidate_id"],
            "package_sha256": _sha256(target / "spritesheet.webp"),
            "package_path": str(target),
        },
    )
    session.transition("installed", artifact_paths=[installation], decision="verified selected Hatch pet installed")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--install-root", type=Path)
    args = parser.parse_args()
    try:
        print(install_selected_pet(args.session_dir, install_root=args.install_root))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
