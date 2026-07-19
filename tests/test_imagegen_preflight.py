from __future__ import annotations

from pathlib import Path

from scripts.imagegen_preflight import inspect_imagegen


def test_preflight_never_returns_a_key_and_reports_missing_cli(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-value")

    result = inspect_imagegen(cli_path=tmp_path / "missing-image-gen.py")

    assert result["status"] == "blocked"
    assert result["openai_api_key_configured"] is True
    assert "secret-value" not in str(result)


def test_preflight_reports_ready_to_attempt_without_validating_the_secret(tmp_path: Path, monkeypatch):
    cli = tmp_path / "image_gen.py"
    cli.write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "configured")

    result = inspect_imagegen(cli_path=cli)

    assert result["status"] == "ready_to_attempt"
    assert result["model"] == "gpt-image-2"
