from __future__ import annotations

import json
from pathlib import Path

from scripts.hatch_base_cli import complete_base_job


def prepared_run(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    (run / "prompts").mkdir(parents=True)
    (run / "prompts" / "base-pet.md").write_text("safe prompt", encoding="utf-8")
    (run / "imagegen-jobs.json").write_text(
        json.dumps({"jobs": [{"id": "base", "status": "pending", "prompt_file": "prompts/base-pet.md", "output_path": "decoded/base.png"}]}),
        encoding="utf-8",
    )
    return run


def test_base_cli_uses_ephemeral_provider_configuration_and_updates_official_manifest(tmp_path: Path, monkeypatch, fake_imagegen):
    run = prepared_run(tmp_path)
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    captured = {}

    def fake_run(command, *, env, check):
        captured["command"] = command
        captured["base_url"] = env.get("OPENAI_BASE_URL")
        captured["key"] = env.get("OPENAI_API_KEY")
        output = Path(command[command.index("--out") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"png")

    monkeypatch.setattr("scripts.hatch_base_cli.subprocess.run", fake_run)

    complete_base_job(run, api_key_env="USER_IMAGE_KEY", image_base_url="https://example.invalid/v1")

    manifest = json.loads((run / "imagegen-jobs.json").read_text(encoding="utf-8"))
    assert manifest["jobs"][0]["status"] == "complete"
    assert (run / "references" / "canonical-base.png").read_bytes() == b"png"
    assert captured["base_url"] == "https://example.invalid/v1"
    assert captured["key"] == "secret"
    assert "secret" not in (run / "imagegen-jobs.json").read_text(encoding="utf-8")


def test_base_cli_refuses_to_run_without_the_user_selected_key_environment(tmp_path: Path, monkeypatch, fake_imagegen):
    run = prepared_run(tmp_path)
    monkeypatch.delenv("MISSING_KEY", raising=False)

    try:
        complete_base_job(run, api_key_env="MISSING_KEY", image_base_url=None)
    except RuntimeError as error:
        assert "MISSING_KEY" in str(error)
    else:
        raise AssertionError("missing provider key must fail")
