"""Robustness tests for adversarially-found validator gaps.

The validator must raise ValueError (not TypeError/KeyError) on malformed input,
and must reject structurally-empty candidates. Fail-closed must hold.
"""
import json
import pytest
from pathlib import Path

from candidate_validator import validate_and_record
from session_contract import ProductSession


def _good(direction: str) -> dict:
    return {
        "candidate_id": f"{direction}-1",
        "ip_name": f"Pet {direction}",
        "display_name": f"Pet / {direction}",
        "description": "a compact endearing companion",
        "form_metaphor": f"a {direction} shaped form",
        "silhouette_tokens": [f"{direction} silhouette"],
        "palette_tokens": [f"{direction} palette"],
        "material_tokens": ["matte ceramic shell"],
        "signature_hook": f"one {direction} marker",
        "interaction_signature": f"it {direction}s near the user",
        "board_composition": f"{direction} reading sequence",
        "anti_drift": ["no literal animal", "no generic blob"],
    }


def _chart_ready(root: Path) -> Path:
    s = ProductSession.create(root)
    chart = s.write_public("chart-ready.json", {})
    s.transition("chart_ready", artifact_paths=[chart], decision="computed")
    return root


def test_non_dict_candidate_raises_valueerror_not_typeerror(tmp_path: Path):
    """Was: TypeError at candidate_id access before the isinstance(dict) guard."""
    _chart_ready(tmp_path / "session")
    for bad in (None, "a-string", 42, ["a", "list"]):
        with pytest.raises(ValueError, match="object|candidate"):
            validate_and_record([bad, _good("beacon"), _good("bridge")],
                tmp_path / "session", source_profile_sha256="x", evidence_refs=[])


def test_empty_visual_token_list_is_rejected(tmp_path: Path):
    """Was: _as_text_list([]) returned [] so silhouette_tokens=[] was accepted."""
    _chart_ready(tmp_path / "session")
    for field in ("silhouette_tokens", "palette_tokens", "material_tokens"):
        bad = _good("shelter")
        bad[field] = []
        with pytest.raises(ValueError, match="empty|must"):
            validate_and_record([bad, _good("beacon"), _good("bridge")],
                tmp_path / "session", source_profile_sha256="x", evidence_refs=[])


def test_non_list_evidence_refs_is_rejected(tmp_path: Path):
    """Was: list('not-a-list') coerced a string to char list."""
    _chart_ready(tmp_path / "session")
    with pytest.raises(ValueError, match="evidence_refs"):
        validate_and_record([_good("shelter"), _good("beacon"), _good("bridge")],
            tmp_path / "session", source_profile_sha256="x", evidence_refs="not-a-list")


def test_non_string_source_hash_is_rejected(tmp_path: Path):
    _chart_ready(tmp_path / "session")
    with pytest.raises(ValueError, match="source_profile_sha256"):
        validate_and_record([_good("shelter"), _good("beacon"), _good("bridge")],
            tmp_path / "session", source_profile_sha256=None, evidence_refs=[])


def test_non_string_token_element_is_rejected(tmp_path: Path):
    _chart_ready(tmp_path / "session")
    bad = _good("shelter")
    bad["silhouette_tokens"] = ["ok", 42, "bad"]
    with pytest.raises(ValueError, match="token list|strings"):
        validate_and_record([bad, _good("beacon"), _good("bridge")],
            tmp_path / "session", source_profile_sha256="x", evidence_refs=[])
