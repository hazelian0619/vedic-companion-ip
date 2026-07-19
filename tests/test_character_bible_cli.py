from __future__ import annotations

import json
from pathlib import Path

from scripts.render_character_bible_cli import render_character_bible_cli


def _candidate(candidate_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "ip_name": "Tavi",
        "display_name": "Tavi / Beacon",
        "description": "A compact companion with one focused signal.",
        "form_metaphor": "A small upright keeper carrying one focused guiding signal.",
        "silhouette_tokens": ["soft vertical crown", "compact balanced body"],
        "palette_tokens": ["supporting outer field", "one focused active accent"],
        "material_tokens": ["soft layered outer surface"],
        "signature_hook": "One focused signal held on the central axis.",
        "anti_drift": ["no scenery"],
    }


def test_character_bible_cli_uses_one_official_base_and_never_persists_provider_credentials(tmp_path: Path, monkeypatch):
    candidates = tmp_path / "safe-candidates.json"
    candidates.write_text(json.dumps({"candidates": [_candidate("a")]}), encoding="utf-8")
    base = tmp_path / "canonical-base.png"
    base.write_bytes(b"base")
    out = tmp_path / "character-bible.png"
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    captured = {}

    def fake_run(command, *, env, check):
        captured["command"] = command
        captured["key"] = env["OPENAI_API_KEY"]
        captured["base_url"] = env["OPENAI_BASE_URL"]
        Path(command[command.index("--out") + 1]).write_bytes(b"board")

    monkeypatch.setattr("scripts.render_character_bible_cli.subprocess.run", fake_run)

    result = render_character_bible_cli(
        candidates,
        "a",
        base,
        out,
        api_key_env="USER_IMAGE_KEY",
        image_base_url="https://provider.invalid/v1",
        board_system="professional-editorial-v2",
    )

    assert result == out
    assert captured["command"][captured["command"].index("edit") + 1 :].count("--image") == 1
    assert str(base) in captured["command"]
    assert captured["key"] == "secret"
    assert captured["base_url"] == "https://provider.invalid/v1"
    manifest = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
    assert manifest["reference_paths"] == [str(base)]
    assert manifest["board_system"] == "professional-editorial-v2"
    assert "secret" not in out.with_suffix(".json").read_text(encoding="utf-8")
    assert "secret" not in out.with_suffix(".prompt.md").read_text(encoding="utf-8")
