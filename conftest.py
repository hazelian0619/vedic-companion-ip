"""Pytest root conftest: make skill/ the single import source for tests.

This lets `pytest` run without `PYTHONPATH=skill:.` and removes the need for
duplicate module copies at the repo root (those are git-ignored/removed; the
canonical modules live under skill/).
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent
_SKILL = _ROOT / "skill"
if str(_SKILL) not in sys.path:
    sys.path.insert(0, str(_SKILL))


@pytest.fixture
def fake_imagegen(tmp_path, monkeypatch):
    """Point every imagegen-CLI path at a fake file so unit tests that monkeypatch
    subprocess.run don't depend on a locally-installed imagegen CLI (absent in CI).
    Covers both hatch_base_cli.IMAGE_GEN and render_character_bible_cli.IMAGE_GEN."""
    fake = tmp_path / "fake_image_gen.py"
    fake.write_text("# fake imagegen CLI for unit tests", encoding="utf-8")
    monkeypatch.setattr("scripts.hatch_base_cli.IMAGE_GEN", fake)
    monkeypatch.setattr("scripts.render_character_bible_cli.IMAGE_GEN", fake)
    return fake

