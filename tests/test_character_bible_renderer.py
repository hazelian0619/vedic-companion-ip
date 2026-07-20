from __future__ import annotations

from character_bible import build_render_request


def test_render_request_keeps_base_first_and_board_reference_second():
    request = build_render_request(
        {
            "official_base_path": "/tmp/base.png",
            "board_reference_path": "/tmp/board-reference.png",
            "ip_name": "Meridian",
            "display_name": "Meridian Steward",
            "form_metaphor": "a bell-shaped keeper",
            "silhouette_tokens": ["pointed cowl"],
            "palette_tokens": ["pale blue", "amber"],
            "material_tokens": ["felted wool"],
            "signature_hook": "one amber chest dial",
            "anti_drift": ["no scenery"],
        }
    )

    assert request["reference_paths"] == ["/tmp/base.png", "/tmp/board-reference.png"]
    assert "render legible integrated typography" in request["prompt"].lower()
    assert "derive the palette" in request["prompt"].lower()
