#!/usr/bin/env python3
"""Create a private companion session: run local chart computation, stop at chart_ready.

This script is CREDENTIAL-FREE. It runs the local deterministic Vedic compute
(VEDIC_PY: PyJHora + Swiss Ephemeris), writes the private chart-report + the
de-identified pet-profile (0o600), and advances the session to chart_ready.

Candidate AUTHORING is a separate, credential-bearing step —
``scripts/author_candidates.py`` — which calls an LLM to draft 3 candidates and
gates them via ``candidate_validator``. Keeping compute and authoring split means
the image-API key is only ever needed for the authoring step, and the privacy
boundary between local facts and external calls stays explicit.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parent.parent  # skill/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from session_contract import ProductSession  # noqa: E402

_DEFAULT_VEDIC_PYTHON = Path(
    os.environ.get(
        "VEDIC_PY",
        str(Path.home() / ".claude" / "skills" / "vedic-calculator" / "venv" / "bin" / "python"),
    )
)


def _succeeded(result: object) -> bool:
    if result is True:
        return True
    if not isinstance(result, Iterable):
        return False
    return all(bool(getattr(item, "ok", False)) for item in result)


def run_private_compute(
    intake_path: Path, outdir: Path, *, vedic_python: Path = _DEFAULT_VEDIC_PYTHON
) -> bool:
    if not vedic_python.is_file():
        raise RuntimeError(f"Vedic Python runtime not found: {vedic_python}")
    command = [
        str(vedic_python),
        str(ROOT / "scripts" / "compute_chart_report.py"),
        "--intake",
        str(intake_path),
        "--outdir",
        str(outdir),
    ]
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
) -> ProductSession:
    """Run local compute and stop at chart_ready. Candidate authoring is a separate step."""
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
    session.transition(
        "chart_ready", artifact_paths=[], decision="local chart computation accepted"
    )
    return session


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--session-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        session = prepare_session(args.intake, args.session_dir)
        print(session.root)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
