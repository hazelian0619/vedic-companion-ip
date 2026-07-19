from __future__ import annotations

from board_system import resolve_board_system
from character_bible import build_render_request


def test_professional_editorial_board_system_has_traceable_sources_without_a_house_style():
    system = resolve_board_system("professional-editorial-v2")

    text = system["prompt"].lower()
    sources = system["sources"].lower()
    assert "turnaround" in text
    assert "must-preserve" in text
    assert "international typographic style" in sources
    assert "museum collection documentation" in sources
    assert "production character bible" in sources
    assert "navy" not in text
    assert "copper" not in text
    assert "meridian" not in text
    assert "house palette" in text
    assert "house material" in text
    assert "information-rich but not crowded" in text
    assert "do not use paragraph copy" in text


def test_board_request_needs_only_the_official_base_when_a_board_system_is_selected():
    request = build_render_request(
        {
            "official_base_path": "/tmp/base.png",
            "board_system": "professional-editorial-v2",
            "ip_name": "Pilot",
            "display_name": "Pilot",
            "form_metaphor": "a compact guiding keeper",
            "silhouette_tokens": ["clear crown"],
            "palette_tokens": ["dominant field", "light face zone"],
            "material_tokens": ["tactile outer layer"],
            "signature_hook": "one centered signal",
            "anti_drift": ["no scenery"],
        }
    )

    assert request["reference_paths"] == ["/tmp/base.png"]
    assert "source foundations" in request["prompt"].lower()
    assert "reference image" not in request["prompt"].lower()
    assert "information-rich but not crowded" in request["prompt"].lower()
