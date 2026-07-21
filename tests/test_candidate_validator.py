"""Tests for the candidate validator: the hard privacy gate on LLM-authored candidates.

These test the GATE (deterministic invariants), not the LLM authoring (non-deterministic).
The validator must: accept 3 schema-clean distinct candidates; reject unknown fields,
astrology terms (English + Chinese), privacy leaks, and non-distinct (recolored/identical)
directions. All fail-closed.
"""
import json
import pytest
from pathlib import Path

from candidate_validator import validate_and_record, RecordedCandidates
from session_contract import ProductSession


def _good(direction: str) -> dict:
    """A schema-clean candidate for one direction (distinct form + silhouette)."""
    return {
        "candidate_id": f"{direction}-abc123-1",
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


def _chart_ready_session(root: Path) -> ProductSession:
    s = ProductSession.create(root)
    chart = s.write_public("chart-ready.json", {})
    s.transition("chart_ready", artifact_paths=[chart], decision="computed")
    return s


# ---------------- accept path ---------------- #

def test_accepts_three_clean_distinct_candidates(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    cands = [_good("shelter"), _good("beacon"), _good("bridge")]
    r = validate_and_record(
        cands, tmp_path / "session",
        source_profile_sha256="deadbeef", evidence_refs=["asc_sign:Aries"],
    )
    assert isinstance(r, RecordedCandidates)
    pub = json.loads(r.candidates_path.read_text(encoding="utf-8"))
    assert len(pub["candidates"]) == 3
    manifest = json.loads((tmp_path / "session" / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "candidates_ready"


def test_records_private_ledger_with_hashes(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    r = validate_and_record(
        [_good("shelter"), _good("beacon"), _good("bridge")], tmp_path / "session",
        source_profile_sha256="abc", evidence_refs=["asc_sign:Aries"], llm_model="gpt-5.5",
    )
    ledger = json.loads(r.private_ledger_path.read_text(encoding="utf-8"))
    assert ledger["authored_by"] == "llm"
    assert ledger["llm_model"] == "gpt-5.5"
    assert ledger["source_profile_sha256"] == "abc"
    assert len(ledger["candidate_hashes"]) == 3
    assert all("sha256" in h for h in ledger["candidate_hashes"])


def test_public_candidates_carry_no_evidence_refs(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    r = validate_and_record(
        [_good("shelter"), _good("beacon"), _good("bridge")], tmp_path / "session",
        source_profile_sha256="x", evidence_refs=["asc_sign:Aries", "planet:Sun:sign:Leo:house:10"],
    )
    pub_text = r.candidates_path.read_text(encoding="utf-8")
    assert "evidence_refs" not in pub_text
    assert "source_profile_sha256" not in pub_text


# ---------------- reject: count + id ---------------- #

def test_rejects_two_candidates(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    with pytest.raises(ValueError, match="three"):
        validate_and_record([_good("shelter"), _good("beacon")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


def test_rejects_duplicate_ids(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    a, b, c = _good("shelter"), _good("beacon"), _good("bridge")
    c["candidate_id"] = a["candidate_id"]
    with pytest.raises(ValueError, match="unique"):
        validate_and_record([a, b, c], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


# ---------------- reject: schema whitelist ---------------- #

def test_rejects_unknown_field(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    bad = _good("shelter"); bad["private_rationale"] = "leak"
    with pytest.raises(ValueError, match="unknown"):
        validate_and_record([bad, _good("beacon"), _good("bridge")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


def test_rejects_missing_required_field(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    bad = _good("shelter"); del bad["signature_hook"]
    with pytest.raises(ValueError, match="missing"):
        validate_and_record([bad, _good("beacon"), _good("bridge")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


# ---------------- reject: privacy + astrology ---------------- #

def test_rejects_english_astrology_term(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    bad = _good("shelter"); bad["description"] = "ruled by Saturn"
    with pytest.raises(ValueError, match="astrology"):
        validate_and_record([bad, _good("beacon"), _good("bridge")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


def test_rejects_chinese_astrology_term(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    bad = _good("shelter"); bad["description"] = "这只行星角色的月亮落在上升"
    with pytest.raises(ValueError, match="astrology"):
        validate_and_record([bad, _good("beacon"), _good("bridge")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


def test_rejects_privacy_leak_date_time(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    bad = _good("shelter"); bad["description"] = "born 1997-08-12 at 23:30"
    with pytest.raises(ValueError, match="privacy"):
        validate_and_record([bad, _good("beacon"), _good("bridge")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


def test_rejects_privacy_leak_coordinates(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    bad = _good("shelter"); bad["description"] = "located at 28.123,113.456"
    with pytest.raises(ValueError, match="privacy"):
        validate_and_record([bad, _good("beacon"), _good("bridge")], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


# ---------------- reject: non-distinct ---------------- #

def test_rejects_three_identical_directions(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    a = _good("shelter")
    b = _good("shelter"); b["candidate_id"] = "shelter-2"
    c = _good("shelter"); c["candidate_id"] = "shelter-3"
    with pytest.raises(ValueError, match="distinct"):
        validate_and_record([a, b, c], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


def test_rejects_recolored_pair_same_form_and_silhouette(tmp_path: Path):
    # Same form + same silhouette, only palette differs => "recolored" => reject.
    _chart_ready_session(tmp_path / "session")
    a = _good("shelter")
    b = _good("shelter"); b["candidate_id"] = "shelter-2"; b["palette_tokens"] = ["different palette"]
    c = _good("beacon")
    with pytest.raises(ValueError, match="distinct"):
        validate_and_record([a, b, c], tmp_path / "session",
            source_profile_sha256="x", evidence_refs=[])


# ---------------- fail-closed: no public write on failure ---------------- #

def test_failure_does_not_advance_session_state(tmp_path: Path):
    _chart_ready_session(tmp_path / "session")
    with pytest.raises(ValueError):
        validate_and_record([_good("shelter"), _good("shelter"), _good("shelter")],
            tmp_path / "session", source_profile_sha256="x", evidence_refs=[])
    manifest = json.loads((tmp_path / "session" / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "chart_ready"  # unchanged
    assert not (tmp_path / "session" / "safe-candidates.json").exists()
