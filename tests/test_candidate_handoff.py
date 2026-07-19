from __future__ import annotations

import pytest

from candidate_handoff import build_board_input, build_hatch_handoff


def safe_candidate() -> dict:
    return {
        "ip_name": "Meridian",
        "display_name": "Meridian / 司辰",
        "subject_archetype": "a compact luminous hermit-guide companion",
        "form_metaphor": "a bell-shaped keeper that points gently forward",
        "silhouette_tokens": ["peaked soft cowl", "rounded bell body", "wide stable base"],
        "palette_tokens": ["pale silvery blue", "warm ivory", "amber accent"],
        "material_tokens": ["felted wool", "ribbed ceramic", "patinated metal"],
        "signature_hook": "one amber compass dial fused to the chest",
        "interaction_signature": "It waits beside the user, then points to one calm next step.",
        "board_composition": "Use a vertical evidence axis that narrows toward one clear next action.",
        "anti_drift": ["no text on the pet", "no scenery", "do not copy the reference character"],
        "polished_prompt": "Create a compact luminous companion with a pale felted cowl and one amber chest dial.",
    }


def test_build_hatch_handoff_contains_only_official_hatch_fields():
    handoff = build_hatch_handoff(safe_candidate(), candidate_id="meridian-o4")

    assert set(handoff) == {
        "pet_name",
        "pet_id",
        "display_name",
        "description",
        "pet_notes",
        "style_notes",
    }
    assert handoff["pet_id"] == "meridian-o4"
    assert "waits beside the user" in handoff["pet_notes"]
    assert "style_preset" not in handoff
    assert "Saturn" not in " ".join(str(value) for value in handoff.values())


def test_build_board_input_rejects_private_or_astrology_content():
    candidate = safe_candidate()
    candidate["private_rationale"] = "Saturn in Sagittarius from 1990-01-01"

    with pytest.raises(ValueError, match="unsafe candidate content"):
        build_board_input(
            candidate,
            official_base_path="/tmp/official-base.png",
            board_reference_path="/tmp/board-reference.png",
        )


def test_board_input_requires_an_official_base_image():
    with pytest.raises(ValueError, match="official hatch-pet base"):
        build_board_input(safe_candidate(), official_base_path="", board_reference_path="/tmp/board-reference.png")


def test_board_input_uses_the_default_board_system_without_a_reference_image():
    result = build_board_input(safe_candidate(), official_base_path="/tmp/official-base.png", board_reference_path="")

    assert result["board_reference_path"] == ""
    assert result["board_system"] == "professional-editorial-v3"
    assert result["interaction_signature"] == "It waits beside the user, then points to one calm next step."
