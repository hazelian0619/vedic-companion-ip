#!/usr/bin/env python3
"""Record explicit visual acceptance after Hatch deterministic QA artifacts exist."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


_STATES = ("idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review")


def _text(value: str, field: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must be non-empty")
    return normalized


def _validated(path: Path) -> bool:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("ok") is True
    except (OSError, json.JSONDecodeError):
        return False


def record_visual_qa(run_dir: Path, *, reviewer: str, note: str) -> Path:
    run = Path(run_dir).resolve()
    if not _validated(run / "final" / "validation.json"):
        raise ValueError("deterministic atlas validation must pass before visual QA")
    if not _validated(run / "qa" / "review.json"):
        raise ValueError("frame inspection must pass before visual QA")
    if not (run / "qa" / "contact-sheet.png").is_file():
        raise ValueError("contact sheet is required before visual QA")
    missing_previews = [state for state in _STATES if not (run / "qa" / "previews" / f"{state}.gif").is_file()]
    if missing_previews:
        raise ValueError(f"visual QA requires previews for: {', '.join(missing_previews)}")
    artifact = run / "qa" / "visual-qa.json"
    artifact.write_text(
        json.dumps({"ok": True, "reviewer": _text(reviewer, "reviewer"), "note": _text(note, "note")}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", required=True)
    args = parser.parse_args()
    try:
        print(record_visual_qa(args.run_dir, reviewer=args.reviewer, note=args.note))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
