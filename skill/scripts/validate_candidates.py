#!/usr/bin/env python3
"""Ad-hoc validate+record of a candidate draft JSON.

Use when author_candidates wrote a private draft but validation failed (state
still chart_ready) and you want to retry — possibly after hand-editing the
draft — without re-calling the LLM.

Reads:
  --draft     a JSON file {"candidates": [c1, c2, c3]}  (LLM-authored, ungated)
  --session-dir the product session (must be in chart_ready)
  --profile   the private pet-profile.json (for evidence_refs + source hash)

Writes public safe-candidates.json + private ledger; advances to candidates_ready.
Fail-closed on any privacy/schema violation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # skill/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from candidate_validator import validate_and_record  # noqa: E402


def _load_profile(profile_path: Path) -> tuple[list[str], str]:
    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    evidence = payload.get("design_safe_evidence") or {}
    refs = evidence.get("evidence_refs") or []
    if not isinstance(refs, list):
        raise ValueError("profile design_safe_evidence.evidence_refs must be a list")
    return [str(r) for r in refs], hashlib.sha256(Path(profile_path).read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--draft", required=True, type=Path)
    p.add_argument("--session-dir", required=True, type=Path)
    p.add_argument("--profile", required=True, type=Path)
    args = p.parse_args()
    try:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        candidates = draft.get("candidates") if isinstance(draft, dict) else draft
        if not isinstance(candidates, list):
            raise ValueError("draft must be a JSON object with a 'candidates' list")
        refs, source_hash = _load_profile(args.profile)
        out = validate_and_record(
            candidates, args.session_dir,
            source_profile_sha256=source_hash, evidence_refs=refs, llm_model="(ad-hoc)",
        )
        print(out)
        return 0
    except (OSError, RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
