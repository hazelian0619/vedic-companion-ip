from __future__ import annotations

import pytest

from character_bible import build_visual_board_prompt


def safe_board_input() -> dict:
    return {
        "official_base_path": "/tmp/official-base.png",
        "board_reference_path": "/tmp/character-bible-reference.png",
        "ip_name": "Meridian",
        "display_name": "Meridian Steward",
        "form_metaphor": "a bell-shaped keeper that points gently forward",
        "silhouette_tokens": ["peaked soft cowl", "rounded bell body", "wide stable base"],
        "palette_tokens": ["pale silvery blue", "warm ivory", "amber accent"],
        "material_tokens": ["felted wool", "ribbed ceramic", "patinated metal"],
        "signature_hook": "one amber compass dial fused to the chest",
        "interaction_signature": "It waits beside the user, then points to one calm next step.",
        "board_composition": "Use a vertical evidence axis that narrows toward one clear next action.",
        "anti_drift": ["no text on the pet", "no scenery", "keep the pale luminous palette"],
    }


def test_visual_board_prompt_grounds_all_views_in_the_official_base():
    prompt = build_visual_board_prompt(
        {**safe_board_input(), "board_reference_path": "", "board_system": "professional-editorial-v3"}
    )

    assert "official canonical base" in prompt.lower()
    assert "do not redesign" in prompt.lower()
    assert "turnaround" in prompt.lower()
    assert "render legible integrated typography" in prompt.lower()
    assert "derive the palette" in prompt.lower()
    assert "waits beside the user" in prompt.lower()
    assert "vertical evidence axis" in prompt.lower()
    assert "generic catalog grid" in prompt.lower()
    assert "behavioral proof sequence" in prompt.lower()
    assert "before, response, and resolve" in prompt.lower()
    assert "not a uniform set of tiles" in prompt.lower()
    assert len(prompt) <= 3800
    assert "deep navy" not in prompt.lower()
    assert "antique copper" not in prompt.lower()
    assert "copper-outline" not in prompt.lower()
    assert "seven-swatch" not in prompt.lower()
    assert "warm-ivory" not in prompt.lower()


def test_visual_board_prompt_rejects_private_or_astrology_terms():
    unsafe = safe_board_input()
    unsafe["form_metaphor"] = "Saturn holds the chart's long path"

    with pytest.raises(ValueError, match="unsafe board input"):
        build_visual_board_prompt(unsafe)


def test_visual_board_prompt_rejects_a_provider_unsafe_length_before_rendering():
    oversized = {
        **safe_board_input(),
        "board_reference_path": "",
        "board_system": "professional-editorial-v3",
        "form_metaphor": "responsive companion " * 600,
    }

    with pytest.raises(ValueError, match="provider-safe limit"):
        build_visual_board_prompt(oversized)
