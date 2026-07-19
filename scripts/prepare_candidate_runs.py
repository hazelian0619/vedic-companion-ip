#!/usr/bin/env python3
"""Prepare three session-owned official Hatch runs without generating images."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from session_contract import ProductSession


ALLOWED_FIELDS = frozenset(
    {
        "candidate_id",
        "ip_name",
        "display_name",
        "description",
        "form_metaphor",
        "silhouette_tokens",
        "palette_tokens",
        "material_tokens",
        "signature_hook",
        "anti_drift",
    }
)
LIST_FIELDS = frozenset({"silhouette_tokens", "palette_tokens", "material_tokens", "anti_drift"})
FORBIDDEN = re.compile(
    r"\b(?:birth|born|date of birth|latitude|longitude|coordinate|timezone|chart|astrolog|horoscope|zodiac|ascendant|nakshatra|dasha|ayanamsa|ephemeris|saturn|jupiter|rahu|ketu)\b",
    re.IGNORECASE,
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not (normalized := " ".join(value.split())):
        raise ValueError(f"unsafe candidate: {field} must be non-empty text")
    return normalized


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("unsafe candidate: candidate_id must have letters or digits")
    return slug


def validate_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict) or set(candidate) != ALLOWED_FIELDS:
        raise ValueError("unsafe candidate: exact visual-safe schema required")

    clean: dict[str, Any] = {}
    for field in ALLOWED_FIELDS - LIST_FIELDS:
        clean[field] = _text(candidate[field], field)
    clean["candidate_id"] = _slug(clean["candidate_id"])
    for field in LIST_FIELDS:
        values = candidate[field]
        if not isinstance(values, list) or not values:
            raise ValueError(f"unsafe candidate: {field} must be a non-empty text list")
        clean[field] = [_text(value, field) for value in values]

    if FORBIDDEN.search(json.dumps(clean, ensure_ascii=False)):
        raise ValueError("unsafe candidate: private or chart-derived wording detected")
    return clean


def load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"candidates"} or not isinstance(payload["candidates"], list):
        raise ValueError("unsafe candidate manifest: expected only a candidates array")
    if len(payload["candidates"]) != 3:
        raise ValueError("unsafe candidate manifest: exactly three candidates are required")
    candidates = [validate_candidate(item) for item in payload["candidates"]]
    if len({item["candidate_id"] for item in candidates}) != 3:
        raise ValueError("unsafe candidate manifest: candidate_id values must be unique")
    return candidates


def prepare_run(candidate: dict[str, Any], output_dir: Path, hatch_pet_dir: Path, force: bool) -> Path:
    run_dir = output_dir / candidate["candidate_id"] / "hatch-pet-run"
    command = [
        sys.executable,
        str(hatch_pet_dir / "scripts" / "prepare_pet_run.py"),
        "--pet-name", candidate["ip_name"],
        "--pet-id", candidate["candidate_id"],
        "--display-name", candidate["display_name"],
        "--description", candidate["description"],
        "--output-dir", str(run_dir),
        "--pet-notes", f"{candidate['form_metaphor']} Silhouette: {', '.join(candidate['silhouette_tokens'])}. Signature: {candidate['signature_hook']}. Avoid: {'; '.join(candidate['anti_drift'])}.",
        "--style-notes", f"Palette: {', '.join(candidate['palette_tokens'])}. Materials: {', '.join(candidate['material_tokens'])}. Keep the character compact and readable at pet size.",
    ]
    if force:
        command.append("--force")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "official hatch-pet scaffolding failed")
    return run_dir.resolve()


def prepare_candidate_runs(session_root: Path, *, hatch_pet_dir: Path, force: bool = False) -> Path:
    session = ProductSession.create(Path(session_root))
    manifest = json.loads((session.root / "session.json").read_text(encoding="utf-8"))
    if manifest.get("state") != "candidates_ready":
        raise ValueError("candidate runs require a session with compiled candidates")
    candidates = load_candidates(session.root / "safe-candidates.json")
    output_dir = session.root / "candidate-runs"
    prepared = []
    for candidate in candidates:
        run_dir = prepare_run(candidate, output_dir, Path(hatch_pet_dir), force)
        if session.root not in run_dir.parents:
            raise ValueError("official Hatch run must remain inside the product session")
        prepared.append(
            {
                "candidate_id": candidate["candidate_id"],
                "hatch_run_dir": str(run_dir.relative_to(session.root)),
                "selection_status": "unselected",
            }
        )
    run_manifest = session.write_public(
        "candidate-runs.json",
        {
            "version": 1,
            "candidates": prepared,
            "selection_rule": "only one user-selected candidate may continue to animation",
        },
    )
    session.transition(
        "candidate_runs_ready",
        artifact_paths=[run_manifest],
        decision="three official Hatch candidate runs prepared inside the session",
    )
    return run_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--hatch-pet-dir", type=Path, default=Path.home() / ".codex" / "skills" / "hatch-pet")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        helper = args.hatch_pet_dir / "scripts" / "prepare_pet_run.py"
        if not helper.is_file():
            raise ValueError(f"official hatch-pet helper not found: {helper}")
        print(prepare_candidate_runs(args.session_dir, hatch_pet_dir=args.hatch_pet_dir, force=args.force))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
