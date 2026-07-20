"""Pytest root conftest: make skill/ the single import source for tests.

This lets `pytest` run without `PYTHONPATH=skill:.` and removes the need for
duplicate module copies at the repo root (those are git-ignored/removed; the
canonical modules live under skill/).
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_SKILL = _ROOT / "skill"
if str(_SKILL) not in sys.path:
    sys.path.insert(0, str(_SKILL))
