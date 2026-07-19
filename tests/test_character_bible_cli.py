from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from scripts.render_character_bible_cli import render_character_bible_cli
from session_contract import ProductSession


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


def _accepted_base_session(tmp_path: Path) -> tuple[ProductSession, Path]:
    session = ProductSession.create(tmp_path / "session")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="fixture")
    candidates = session.write_public("safe-candidates.json", {"candidates": [_candidate("a")]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="fixture")
    run = session.root / "candidate-runs" / "a" / "hatch-pet-run"
    base = run / "references" / "canonical-base.png"
    base.parent.mkdir(parents=True)
    base.write_bytes(b"base")
    runs = session.write_public("candidate-runs.json", {"candidates": [{"candidate_id": "a", "hatch_run_dir": str(run.relative_to(session.root))}]})
    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="fixture")
    bases = session.write_public(
        "candidate-bases.json",
        {
            "bases": [
                {
                    "candidate_id": "a",
                    "hatch_run_dir": str(run.relative_to(session.root)),
                    "canonical_base": str(base.relative_to(session.root)),
                    "base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
                }
            ]
        },
    )
    session.transition("candidate_bases_ready", artifact_paths=[bases], decision="fixture")
    return session, base


def test_character_bible_cli_uses_the_accepted_session_base_and_never_persists_provider_credentials(tmp_path: Path, monkeypatch):
    session, base = _accepted_base_session(tmp_path)
    out = session.root / "candidates" / "a" / "character-bible.png"
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    captured = {}

    def fake_run(command, *, env, check):
        captured["command"] = command
        captured["key"] = env["OPENAI_API_KEY"]
        captured["base_url"] = env["OPENAI_BASE_URL"]
        Path(command[command.index("--out") + 1]).write_bytes(b"board")

    monkeypatch.setattr("scripts.render_character_bible_cli.subprocess.run", fake_run)

    result = render_character_bible_cli(
        session.root,
        "a",
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


def test_character_bible_cli_rejects_a_base_changed_after_acceptance_before_calling_imagegen(tmp_path: Path, monkeypatch):
    session, base = _accepted_base_session(tmp_path)
    base.write_bytes(b"tampered")
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    monkeypatch.setattr("scripts.render_character_bible_cli.subprocess.run", lambda *args, **kwargs: pytest.fail("imagegen must not run"))

    with pytest.raises(ValueError, match="accepted canonical base"):
        render_character_bible_cli(
            session.root,
            "a",
            session.root / "candidates" / "a" / "character-bible.png",
            api_key_env="USER_IMAGE_KEY",
            image_base_url="https://provider.invalid/v1",
        )
