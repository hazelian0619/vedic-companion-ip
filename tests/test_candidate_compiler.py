from __future__ import annotations

import json
from pathlib import Path

from candidate_compiler import _MATERIAL_RELATIONSHIPS, _PALETTE_RELATIONSHIPS, _visual_relationships, compile_candidates
from companion_ip_contract import astrology_term_scan, privacy_scan
from session_contract import ProductSession


def profile_payload() -> dict:
    return {
        "design_safe_evidence": {
            "computation_source": "pyjhora-swiss-ephemeris",
            "provenance_sanitized": True,
            "evidence_refs": [
                "asc_sign:Aries",
                "planet:Sun:sign:Leo:house:10",
                "planet:Moon:sign:Cancer:house:4",
                "planet:Venus:sign:Libra:house:7",
            ],
            "deidentified_facts": {
                "asc_sign": "Aries",
                "atmakaraka": "Sun",
                "mahadasha_lord": "Moon",
                "moon_nakshatra_name": "Ashwini",
                "planets": {
                    "Sun": {"sign": "Leo", "house": 10, "retrograde": False, "dignity": "neutral"},
                    "Moon": {"sign": "Cancer", "house": 4, "retrograde": False, "dignity": "neutral"},
                    "Venus": {"sign": "Libra", "house": 7, "retrograde": False, "dignity": "neutral"},
                },
            },
        }
    }


def _chart_ready_session(root: Path) -> ProductSession:
    session = ProductSession.create(root)
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    return session


def test_compiler_emits_three_visual_safe_candidates_and_private_evidence(tmp_path: Path):
    profile = tmp_path / "pet-profile.json"
    profile.write_text(json.dumps(profile_payload()), encoding="utf-8")
    _chart_ready_session(tmp_path / "session")

    result = compile_candidates(profile, tmp_path / "session")

    public = json.loads(result.candidates_path.read_text(encoding="utf-8"))
    private = json.loads(result.private_ledger_path.read_text(encoding="utf-8"))
    assert len(public["candidates"]) == 3
    assert len({candidate["candidate_id"] for candidate in public["candidates"]}) == 3
    assert {candidate["form_metaphor"] for candidate in public["candidates"]}
    assert {candidate["interaction_signature"] for candidate in public["candidates"]}
    assert {candidate["board_composition"] for candidate in public["candidates"]}
    assert all(not astrology_term_scan(json.dumps(candidate)) for candidate in public["candidates"])
    assert all(privacy_scan(json.dumps(candidate))[0] for candidate in public["candidates"])
    assert "evidence_refs" not in json.dumps(public)
    assert len(private["candidate_evidence"]) == 3
    assert all(len(item["evidence_refs"]) >= 2 for item in private["candidate_evidence"])


def test_compiler_is_deterministic_and_uses_relative_visual_tokens(tmp_path: Path):
    profile = tmp_path / "pet-profile.json"
    profile.write_text(json.dumps(profile_payload()), encoding="utf-8")
    _chart_ready_session(tmp_path / "first")
    _chart_ready_session(tmp_path / "second")

    first = compile_candidates(profile, tmp_path / "first")
    second = compile_candidates(profile, tmp_path / "second")

    assert first.candidates_path.read_bytes() == second.candidates_path.read_bytes()
    candidates = json.loads(first.candidates_path.read_text(encoding="utf-8"))["candidates"]
    forbidden_colors = {"navy", "copper", "ivory", "purple", "beige", "orange"}
    concrete_hues = {
        "moss", "celadon", "vermilion", "mulberry", "blush", "cyan",
        "petrol", "mint", "cinnabar", "cobalt", "lemon", "coral",
        "berry", "cloud", "lime", "saffron", "rose", "indigo",
        "slate", "apricot", "emerald", "pine", "pearl", "scarlet",
        "charcoal", "seafoam", "magenta",
    }
    assert len({tuple(candidate["palette_tokens"]) for candidate in candidates}) == 3
    concrete_materials = {
        "ceramic", "fabric", "aluminum", "resin", "felt", "paper-composite",
        "glass", "rubber", "enamel", "knit", "acrylic", "silicone", "cork",
        "leather", "steel", "wood", "linen", "porcelain", "textile",
    }
    assert len({tuple(candidate["material_tokens"]) for candidate in candidates}) == 3
    for candidate in candidates:
        palette = " ".join(candidate["palette_tokens"]).lower()
        assert not forbidden_colors.intersection(palette.split())
        assert concrete_hues.intersection(palette.split())
        assert "field" not in palette
        materials = " ".join(candidate["material_tokens"]).lower()
        assert concrete_materials.intersection(materials.split())
        assert all("palette" not in token.lower() for token in candidate["material_tokens"])
        assert "chart" not in candidate["interaction_signature"].lower()
        assert "astrolog" not in candidate["board_composition"].lower()
        assert "hood" not in candidate["body_grammar"].lower()


def test_compiler_rejects_an_invalid_or_incomplete_profile(tmp_path: Path):
    profile = tmp_path / "pet-profile.json"
    profile.write_text(json.dumps({"design_safe_evidence": {}}), encoding="utf-8")

    try:
        compile_candidates(profile, tmp_path / "session")
    except ValueError as error:
        assert "pet profile" in str(error).lower()
    else:
        raise AssertionError("expected invalid profile to fail")


def test_visual_dna_vocabulary_never_contains_a_blocked_astrology_substring():
    for relationship in (*_PALETTE_RELATIONSHIPS, *_MATERIAL_RELATIONSHIPS):
        assert not astrology_term_scan(" ".join(relationship))


def test_visual_relationships_are_distinct_for_every_candidate_across_digest_values():
    for digest in ("1" * 64, "a" * 64):
        relationships = [_visual_relationships(direction, digest) for direction in ("shelter", "beacon", "bridge")]
        assert len({tuple(palette) for palette, _ in relationships}) == 3
        assert len({tuple(materials) for _, materials in relationships}) == 3
