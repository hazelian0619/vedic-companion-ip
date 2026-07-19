from __future__ import annotations

import json
import base64
from pathlib import Path

import pytest

from scripts.render_identity_board_cli import render_identity_board_cli
from session_contract import ProductSession


def _candidate(candidate_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "ip_name": f"Pet {candidate_id}",
        "display_name": f"Pet / {candidate_id}",
        "form_metaphor": "a small nested keepsake wrap that has learned to walk beside someone",
        "body_grammar": "An asymmetric wrap-bodied companion with one oversized quilted shoulder flap and two offset soft feet.",
        "silhouette_tokens": ["comma-shaped wrap body", "offset soft feet"],
        "relationship_gesture": "It scoots close and turns its wrap flap outward like a tiny invitation.",
        "tactile_hook": "A pinchable plush edge and raised blanket stitching invite a calming thumb rub.",
        "palette_tokens": ["moss outer structure", "celadon face plane", "vermilion signal detail"],
        "material_tokens": ["matte ceramic outer shell", "woven fabric face surround", "brushed aluminum join"],
        "signature_hook": "one tucked fabric pull tab",
        "default_form_avoids": ["symmetric toy pod silhouette", "central status light or center button", "consumer electronics casing"],
        "anti_drift": ["no literal animal", "no generic blob", "no scenery"],
    }


def _candidates_ready_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "run")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public("safe-candidates.json", {"candidates": [_candidate("a"), _candidate("b"), _candidate("c")]})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    return session


def test_identity_renderer_writes_hero_and_board_without_persisting_credentials(tmp_path: Path, monkeypatch):
    session = _candidates_ready_session(tmp_path)
    imagegen = tmp_path / "image_gen.py"
    imagegen.write_text("", encoding="utf-8")
    monkeypatch.setattr("scripts.render_identity_board_cli.IMAGE_GEN", imagegen)
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    captured: list[tuple[list[str], dict]] = []

    def fake_run(command, **kwargs):
        captured.append((command, kwargs))
        Path(command[command.index("--out") + 1]).write_bytes(b"hero" if command[2] == "generate" else b"board")

    monkeypatch.setattr("scripts.render_identity_board_cli.subprocess.run", fake_run)

    result = render_identity_board_cli(
        session.root,
        "a",
        api_key_env="USER_IMAGE_KEY",
        image_base_url="https://provider.invalid/v1",
    )

    assert result["hero"].is_file()
    assert result["board"].is_file()
    assert [command[2] for command, _ in captured] == ["generate", "edit"]
    assert str(result["hero"]) in captured[1][0]
    assert captured[0][1]["env"]["OPENAI_API_KEY"] == "secret"
    assert captured[0][1]["env"]["OPENAI_BASE_URL"] == "https://provider.invalid/v1"
    manifest = json.loads(result["manifest"].read_text(encoding="utf-8"))
    assert manifest["hero"] == "candidates/a/identity-hero.png"
    assert manifest["identity_board"] == "candidates/a/identity-board.png"
    assert manifest["renderer"] == "official-imagegen-cli"
    assert "secret" not in result["manifest"].read_text(encoding="utf-8")
    assert "secret" not in result["hero_prompt"].read_text(encoding="utf-8")
    assert "secret" not in result["board_prompt"].read_text(encoding="utf-8")


def test_identity_renderer_requires_candidates_ready(tmp_path: Path, monkeypatch):
    session = ProductSession.create(tmp_path / "run")
    imagegen = tmp_path / "image_gen.py"
    imagegen.write_text("", encoding="utf-8")
    monkeypatch.setattr("scripts.render_identity_board_cli.IMAGE_GEN", imagegen)
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")

    with pytest.raises(ValueError, match="candidates_ready"):
        render_identity_board_cli(session.root, "a", api_key_env="USER_IMAGE_KEY", image_base_url=None)


def test_identity_renderer_keeps_a_design_reference_out_of_the_hero_call(tmp_path: Path, monkeypatch):
    session = _candidates_ready_session(tmp_path)
    imagegen = tmp_path / "image_gen.py"
    imagegen.write_text("", encoding="utf-8")
    reference = tmp_path / "editorial-reference.png"
    reference.write_bytes(b"style-only")
    monkeypatch.setattr("scripts.render_identity_board_cli.IMAGE_GEN", imagegen)
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        Path(command[command.index("--out") + 1]).write_bytes(b"image")

    monkeypatch.setattr("scripts.render_identity_board_cli.subprocess.run", fake_run)

    result = render_identity_board_cli(
        session.root,
        "a",
        api_key_env="USER_IMAGE_KEY",
        image_base_url="https://provider.invalid/v1",
        design_reference_path=reference,
    )

    assert [command[2] for command in commands] == ["generate", "edit"]
    assert "--image" not in commands[0]
    assert commands[1].count("--image") == 2
    assert str(result["hero"]) in commands[1]
    assert str(reference) in commands[1]


def test_identity_renderer_supports_an_explicit_same_model_provider_http_fallback(tmp_path: Path, monkeypatch):
    session = _candidates_ready_session(tmp_path)
    monkeypatch.setenv("USER_IMAGE_KEY", "secret")
    calls: list[dict] = []
    curl_commands: list[list[str]] = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            encoded = base64.b64encode(b"provider-image").decode("ascii")
            return {"data": [{"b64_json": encoded}]}

    def fake_post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return Response()

    class CurlResult:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_curl(command, **kwargs):
        curl_commands.append(command)
        assert kwargs["input"] == "Authorization: Bearer secret\n"
        response_path = Path(command[command.index("--output") + 1])
        response_path.write_text(json.dumps({"data": [{"b64_json": base64.b64encode(b"provider-image").decode("ascii")}]}) , encoding="utf-8")
        return CurlResult()

    monkeypatch.setattr("scripts.render_identity_board_cli.requests.post", fake_post)
    monkeypatch.setattr("scripts.render_identity_board_cli.subprocess.run", fake_curl)

    result = render_identity_board_cli(
        session.root,
        "a",
        api_key_env="USER_IMAGE_KEY",
        image_base_url="https://provider.invalid/v1",
        provider_http_fallback=True,
    )

    assert result["hero"].read_bytes() == b"provider-image"
    assert result["board"].read_bytes() == b"provider-image"
    assert [call["url"] for call in calls] == ["https://provider.invalid/v1/images/generations"]
    assert calls[0]["json"]["model"] == "gpt-image-2"
    assert calls[0]["files"] is None
    assert len(curl_commands) == 1
    assert "https://provider.invalid/v1/images/edits" == curl_commands[0][-1]
    assert curl_commands[0].count("-F") == 6
    assert "@-" in curl_commands[0]
    assert "secret" not in result["manifest"].read_text(encoding="utf-8")
