from __future__ import annotations

import json
from pathlib import Path

import pytest

from candidate_compiler import compile_candidates
from candidate_handoff import build_identity_board_input
from companion_ip_contract import astrology_term_scan, privacy_scan
from session_contract import ProductSession


def _profile() -> dict:
    return {
        "design_safe_evidence": {
            "evidence_refs": [
                "asc_sign:Aries",
                "planet:Sun:sign:Leo:house:10",
                "planet:Moon:sign:Cancer:house:4",
                "planet:Venus:sign:Libra:house:7",
            ],
            "deidentified_facts": {
                "asc_sign": "Aries",
                "planets": {
                    "Sun": {"sign": "Leo", "house": 10},
                    "Moon": {"sign": "Cancer", "house": 4},
                    "Venus": {"sign": "Libra", "house": 7},
                },
            },
        }
    }


def _compiled_candidates(tmp_path: Path) -> list[dict]:
    profile = tmp_path / "pet-profile.json"
    profile.write_text(json.dumps(_profile()), encoding="utf-8")
    session = ProductSession.create(tmp_path / "session")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    result = compile_candidates(profile, session.root)
    return json.loads(result.candidates_path.read_text(encoding="utf-8"))["candidates"]


def test_compiler_emits_distinct_safe_art_direction_contracts(tmp_path: Path):
    candidates = _compiled_candidates(tmp_path)

    assert len(candidates) == 3
    required = {"body_grammar", "relationship_gesture", "tactile_hook", "default_form_avoids"}
    assert all(required.issubset(candidate) for candidate in candidates)
    assert len({candidate["body_grammar"] for candidate in candidates}) == 3
    assert len({candidate["relationship_gesture"] for candidate in candidates}) == 3
    assert len({candidate["tactile_hook"] for candidate in candidates}) == 3
    for candidate in candidates:
        public_text = json.dumps(candidate, ensure_ascii=False)
        assert privacy_scan(public_text)[0]
        assert not astrology_term_scan(public_text)
        assert all(candidate[field] for field in required)
        grammar = candidate["body_grammar"].lower()
        assert "symmetric pod" not in grammar
        assert "center button" not in grammar
        assert "oval face window" not in grammar
        avoids = " ".join(candidate["default_form_avoids"]).lower()
        assert "symmetric toy pod" in avoids
        assert "central status light" in avoids
        assert "consumer electronics" in avoids
        assert "face enclosed in a hood" in avoids
        assert "oversized blade, sail, or wing" in avoids
        assert "large separate face applique" in avoids


def test_identity_board_prompts_keep_the_hero_authoritative(tmp_path: Path):
    from identity_board import build_identity_board_requests

    candidate = _compiled_candidates(tmp_path)[0]
    board_input = build_identity_board_input(candidate, design_reference_path="/tmp/editorial-reference.png")

    requests = build_identity_board_requests(board_input)

    assert "non-canonical identity exploration" in requests["hero_prompt"].lower()
    assert candidate["body_grammar"] in requests["hero_prompt"]
    assert candidate["relationship_gesture"] in requests["hero_prompt"]
    assert "symmetric toy pod" in requests["hero_prompt"].lower()
    assert "input image 1 as the exact hero identity" in requests["board_prompt"].lower()
    assert "do not invent a replacement character" in requests["board_prompt"].lower()
    assert "render legible integrated typography" in requests["board_prompt"].lower()
    assert "not a brand campaign" in requests["board_prompt"].lower()
    assert "urls, domains" in requests["board_prompt"].lower()
    assert "four small identity specimens" in requests["board_prompt"].lower()
    assert requests["hero_reference_paths"] == []
    assert requests["board_reference_roles"] == ["hero", "style_only"]
    assert "never a human child face" in requests["hero_prompt"].lower()


def test_identity_board_rejects_private_or_chart_language(tmp_path: Path):
    from identity_board import build_identity_board_requests

    candidate = _compiled_candidates(tmp_path)[0]
    candidate["body_grammar"] = "Saturn makes a small companion"

    with pytest.raises(ValueError, match="unsafe identity board input"):
        build_identity_board_requests(build_identity_board_input(candidate))
