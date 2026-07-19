#!/usr/bin/env python3
"""Verify that a Hatch run has all files required for an installable delivery."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional


_STATES = ("idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review")


def verify_delivery(run_dir: Path, *, install_dir: Optional[Path] = None) -> dict[str, Any]:
    run = Path(run_dir)
    required = [
        "final/spritesheet.webp",
        "final/validation.json",
        "qa/contact-sheet.png",
        "qa/review.json",
    ]
    missing = [relative for relative in required if not (run / relative).is_file()]
    preview_dir = run / "qa" / "previews"
    for state in _STATES:
        if not (preview_dir / f"{state}.gif").is_file():
            missing.append(f"qa/previews/{state}.gif")
    validation = run / "final" / "validation.json"
    if validation.is_file():
        try:
            if json.loads(validation.read_text(encoding="utf-8")).get("ok") is not True:
                missing.append("final/validation.json (ok must be true)")
        except json.JSONDecodeError:
            missing.append("final/validation.json (invalid JSON)")
    frame_review = run / "qa" / "review.json"
    if frame_review.is_file():
        try:
            if json.loads(frame_review.read_text(encoding="utf-8")).get("ok") is not True:
                missing.append("qa/review.json (ok must be true)")
        except json.JSONDecodeError:
            missing.append("qa/review.json (invalid JSON)")
    visual_qa = run / "qa" / "visual-qa.json"
    if not visual_qa.is_file():
        missing.append("qa/visual-qa.json (ok must be true)")
    else:
        try:
            if json.loads(visual_qa.read_text(encoding="utf-8")).get("ok") is not True:
                missing.append("qa/visual-qa.json (ok must be true)")
        except json.JSONDecodeError:
            missing.append("qa/visual-qa.json (invalid JSON)")
    if install_dir is not None:
        install = Path(install_dir)
        for name in ("pet.json", "spritesheet.webp"):
            if not (install / name).is_file():
                missing.append(f"install/{name}")
    return {"ok": not missing, "run_dir": str(run), "missing": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--install-dir", type=Path)
    args = parser.parse_args()
    result = verify_delivery(args.run_dir, install_dir=args.install_dir)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
