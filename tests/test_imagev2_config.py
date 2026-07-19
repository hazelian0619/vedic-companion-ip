from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from imagev2 import resolve_connection


def test_imagev2_uses_explicit_ephemeral_connection(monkeypatch):
    monkeypatch.setenv("IMAGEV2_ENDPOINT", "https://example.test/v1/chat/completions")
    monkeypatch.setenv("IMAGEV2_API_KEY", "ephemeral-test-key")

    endpoint, key = resolve_connection()

    assert endpoint == "https://example.test/v1/chat/completions"
    assert key == "ephemeral-test-key"
