from __future__ import annotations

import pytest

from character_bible import build_design_branch_request


def branch_input() -> dict:
    return {
        "board_reference_path": "/tmp/board-system.png",
        "hatch_seed_prompt": "Create a compact full-body reference sprite for a small bell-shaped keeper.",
        "ip_name": "Pilot",
        "display_name": "Pilot",
        "form_metaphor": "a compact keeper carrying one quiet signal",
        "silhouette_tokens": ["rounded hood", "wide stable base"],
        "palette_tokens": ["reference-derived palette"],
        "material_tokens": ["reference-derived materials"],
        "signature_hook": "one integrated chest marker",
        "anti_drift": ["no scenery"],
    }


def test_design_branch_uses_hatch_seed_and_user_board_reference_only():
    request = build_design_branch_request(branch_input())

    assert request["reference_paths"] == ["/tmp/board-system.png"]
    assert "official hatch-pet seed" in request["board_prompt"].lower()
    assert "render legible integrated typography" in request["board_prompt"].lower()
    assert "deep navy" not in request["board_prompt"].lower()
    assert "antique copper" not in request["board_prompt"].lower()
    assert "no text" in request["identity_reference_prompt"].lower()
    assert request["output_roles"] == ["board", "identity_reference"]


def test_design_branch_identity_reference_extracts_the_character_from_its_parent_board():
    request = build_design_branch_request(branch_input())

    identity_prompt = request["identity_reference_prompt"].lower()
    assert "input image 1: the just-rendered character bible design board" in identity_prompt
    assert "sole visual lineage source" in identity_prompt
    assert "extract the exact same character" in identity_prompt
    assert "user-approved character bible editorial reference" not in identity_prompt


def test_design_branch_rejects_private_seed_content():
    unsafe = branch_input()
    unsafe["hatch_seed_prompt"] = "Born 1997-05-07 with a chart report"

    with pytest.raises(ValueError, match="unsafe design branch input"):
        build_design_branch_request(unsafe)


def test_design_branch_allows_non_astrology_house_style_word_in_official_seed():
    safe = branch_input()
    safe["hatch_seed_prompt"] = "Keep the selected reference's house style without copying its character."

    request = build_design_branch_request(safe)

    assert "house style" in request["board_prompt"]
