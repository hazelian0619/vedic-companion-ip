#!/usr/bin/env python3
"""Print a redaction-safe product-session status for external callers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from session_contract import ProductSession


_NEXT_ACTION = {
    "intake_ready": "compute_private_chart",
    "chart_ready": "compile_candidates",
    "candidates_ready": "prepare_candidate_runs",
    "candidate_runs_ready": "generate_hatch_bases",
    "candidate_bases_ready": "render_character_bibles",
    "candidate_boards_ready": "select_candidate",
    "candidate_selected": "generate_hatch_rows",
    "base_accepted": "generate_hatch_rows",
    "animation_ready": "run_visual_qa_and_package",
    "package_validated": "install_pet",
    "installed": "complete",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidates(session: ProductSession) -> list[dict[str, str]]:
    path = session.root / "safe-candidates.json"
    if not path.is_file():
        return []
    return [
        {"candidate_id": str(item["candidate_id"]), "display_name": str(item.get("display_name", item["candidate_id"]))}
        for item in _load(path).get("candidates", [])
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
    ]


def session_status(session_root: Path) -> dict:
    session = ProductSession.create(Path(session_root))
    manifest = _load(session.root / "session.json")
    state = str(manifest["state"])
    result: dict[str, object] = {
        "session_id": str(manifest["session_id"]),
        "state": state,
        "next_action": _NEXT_ACTION[state],
        "candidates": _candidates(session),
    }
    boards_path = session.root / "candidate-boards.json"
    if state == "candidate_boards_ready" and boards_path.is_file():
        boards_payload = _load(boards_path)
        result["board_system"] = str(boards_payload.get("board_system", ""))
        result["boards"] = [
            {
                "candidate_id": str(item["candidate_id"]),
                "canonical_base": str(item["canonical_base"]),
                "character_bible": str(item["character_bible"]),
            }
            for item in boards_payload.get("boards", [])
            if isinstance(item, dict)
            and all(isinstance(item.get(key), str) for key in ("candidate_id", "canonical_base", "character_bible"))
        ]
        provenance_path = session.root / "candidate-board-provenance.json"
        if provenance_path.is_file():
            provenance = _load(provenance_path)
            board_hash = hashlib.sha256(boards_path.read_bytes()).hexdigest()
            if provenance.get("candidate_boards_sha256") == board_hash:
                result["rendered_board_system"] = str(provenance.get("rendered_board_system", ""))
                result["current_runtime_board_system"] = str(provenance.get("current_runtime_board_system", ""))
    selection_path = session.root / "selection.json"
    if selection_path.is_file():
        selection = _load(selection_path)
        result["selection"] = {"candidate_id": str(selection.get("candidate_id", ""))}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(session_status(args.session_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
