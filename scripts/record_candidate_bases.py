#!/usr/bin/env python3
"""Record the three accepted official Hatch bases before rendering Character Bibles."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from session_contract import ProductSession


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(value: str, field: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must be non-empty")
    return normalized


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _base_job_completed(run_dir: Path) -> None:
    jobs_path = run_dir / "imagegen-jobs.json"
    if not jobs_path.is_file():
        raise ValueError("recorded Hatch run is missing imagegen-jobs.json")
    jobs = _load(jobs_path).get("jobs", [])
    base_job = next((job for job in jobs if isinstance(job, dict) and job.get("id") == "base"), None)
    if not isinstance(base_job, dict) or base_job.get("status") != "complete":
        raise ValueError("recorded Hatch run does not have a completed canonical base job")


def record_candidate_bases(
    session_root: Path,
    bases_by_candidate: dict[str, Path],
    *,
    reviewer: str,
    note: str,
) -> Path:
    session = ProductSession.create(Path(session_root))
    manifest = _load(session.root / "session.json")
    if manifest.get("state") != "candidate_runs_ready":
        raise ValueError("candidate bases require prepared official Hatch runs")
    candidate_ids = [item["candidate_id"] for item in _load(session.root / "safe-candidates.json").get("candidates", [])]
    if set(bases_by_candidate) != set(candidate_ids):
        raise ValueError("candidate bases must include all candidates exactly once")
    run_records = _load(session.root / "candidate-runs.json").get("candidates", [])
    runs = {
        item.get("candidate_id"): item.get("hatch_run_dir")
        for item in run_records
        if isinstance(item, dict) and isinstance(item.get("candidate_id"), str) and isinstance(item.get("hatch_run_dir"), str)
    }
    if set(runs) != set(candidate_ids):
        raise ValueError("candidate run manifest must include all candidates exactly once")

    records = []
    for candidate_id in candidate_ids:
        run_dir = (session.root / runs[candidate_id]).resolve()
        if session.root not in run_dir.parents or not run_dir.is_dir():
            raise ValueError("recorded Hatch run is missing or outside the session")
        expected_base = (run_dir / "references" / "canonical-base.png").resolve()
        base = Path(bases_by_candidate[candidate_id]).resolve()
        if base != expected_base:
            raise ValueError("candidate base must be the canonical base from its recorded Hatch run")
        if not base.is_file() or session.root not in base.parents:
            raise ValueError("candidate canonical base is missing or outside the session")
        _base_job_completed(run_dir)
        records.append(
            {
                "candidate_id": candidate_id,
                "hatch_run_dir": str(run_dir.relative_to(session.root)),
                "canonical_base": str(base.relative_to(session.root)),
                "base_sha256": _sha256(base),
                "reviewer": _text(reviewer, "reviewer"),
                "note": _text(note, "note"),
            }
        )
    bases_manifest = session.write_public("candidate-bases.json", {"bases": records})
    session.transition(
        "candidate_bases_ready",
        artifact_paths=[bases_manifest],
        decision="three official Hatch canonical bases visually accepted",
    )
    return bases_manifest


def _base_argument(value: str) -> tuple[str, Path]:
    candidate_id, separator, path = value.partition("=")
    if not separator or not candidate_id or not path:
        raise argparse.ArgumentTypeError("base entries must use candidate-id=/absolute/path/to/canonical-base.png")
    return candidate_id, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", required=True, type=Path)
    parser.add_argument("--base", required=True, action="append", type=_base_argument)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", required=True)
    args = parser.parse_args()
    try:
        print(record_candidate_bases(args.session_dir, dict(args.base), reviewer=args.reviewer, note=args.note))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
