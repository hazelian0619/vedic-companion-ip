#!/usr/bin/env python3
"""Create a private companion session and compile its three public candidates."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from candidate_compiler import CompiledCandidates, compile_candidates
from session_contract import ProductSession

_DEFAULT_VEDIC_PYTHON = Path(
    os.environ.get("VEDIC_PY", str(Path.home() / ".claude" / "skills" / "vedic-calculator" / "venv" / "bin" / "python"))
)


def _succeeded(result: object) -> bool:
    if result is True:
        return True
    if not isinstance(result, Iterable):
        return False
    return all(bool(getattr(item, "ok", False)) for item in result)


def run_private_compute(intake_path: Path, outdir: Path, *, vedic_python: Path = _DEFAULT_VEDIC_PYTHON) -> bool:
    if not vedic_python.is_file():
        raise RuntimeError(f"Vedic Python runtime not found: {vedic_python}")
    command = [str(vedic_python), str(ROOT / "scripts" / "compute_chart_report.py"), "--intake", str(intake_path), "--outdir", str(outdir)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"local chart computation failed: {detail}")
    return True


def prepare_session(
    intake_path: Path,
    session_root: Path,
    *,
    compute_fn: Callable[[Path, Path], object] = run_private_compute,
) -> CompiledCandidates:
    session = ProductSession.create(Path(session_root))
    chart_dir = session.root / "private" / "chart"
    result = compute_fn(Path(intake_path), chart_dir)
    if not _succeeded(result):
        raise RuntimeError("local chart computation failed")
    for name in ("chart-report.json", "pet-profile.json"):
        artifact = chart_dir / name
        if not artifact.is_file():
            raise RuntimeError(f"local chart computation did not create {name}")
        os.chmod(artifact, 0o600)
    session.transition("chart_ready", artifact_paths=[], decision="local chart computation accepted")
    return compile_candidates(chart_dir / "pet-profile.json", session.root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--session-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = prepare_session(args.intake, args.session_dir)
        print(result.candidates_path)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
