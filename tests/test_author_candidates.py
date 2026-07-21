"""Tests for the LLM candidate drafter. Network is mocked.

Privacy invariant under test: author_candidates sends ONLY deidentified facts to
the LLM — raw birth data, coordinates, timezone, or chart terms that happen to be
in the profile MUST NOT appear in the request body. The LLM's candidate output is
then gated by candidate_validator (tested separately).
"""
import json
import sys
from pathlib import Path

import pytest

# author_candidates lives in skill/scripts; conftest puts skill/ on path, but the
# module is under skill/scripts so import it as scripts.author_candidates.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skill"))
from scripts import author_candidates as ac  # noqa: E402
from session_contract import ProductSession  # noqa: E402


def _good(direction: str, i: int = 1) -> dict:
    return {
        "candidate_id": f"{direction}-{i}",
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


class _FakeResp:
    def __init__(self, payload):
        self._p = payload
        self.status_code = 200
        self.text = ""

    def json(self):
        return self._p


def _profile_with_honeypots() -> dict:
    """A profile that contains deidentified facts AND raw honeypots that must NOT leave."""
    return {
        "design_safe_evidence": {
            "computation_source": "pyjhora-swiss-ephemeris",
            "provenance_sanitized": True,
            "evidence_refs": ["asc_sign:Aries", "planet:Sun:sign:Leo:house:10"],
            "deidentified_facts": {
                "asc_sign": "Aries",
                "atmakaraka": "Sun",
                "mahadasha_lord": "Moon",
                "moon_nakshatra_name": "Ashwini",
                "planets": {
                    "Sun": {"sign": "Leo", "house": 10, "retrograde": False, "dignity": "neutral"},
                },
            },
        },
        # honeypots — these are raw/private and must NEVER be sent to the LLM:
        "birth_date": "1997-08-12",
        "birth_time": "23:30",
        "timezone": "Asia/Shanghai",
        "lat": 28.0,
        "lon": 113.0,
        "private_rationale": "the user was born in Chenzhou",
    }


def _chart_ready_session(root: Path) -> Path:
    s = ProductSession.create(root)
    chart = s.write_public("chart-ready.json", {})
    s.transition("chart_ready", artifact_paths=[chart], decision="computed")
    # place the profile in the private chart dir where author_candidates reads it
    (root / "private" / "chart").mkdir(parents=True, exist_ok=True)
    return root


def test_author_sends_only_deidentified_facts_not_raw_birth_data(tmp_path: Path, monkeypatch):
    sess = _chart_ready_session(tmp_path / "session")
    (sess / "private" / "chart" / "pet-profile.json").write_text(
        json.dumps(_profile_with_honeypots()), encoding="utf-8")

    captured = {}

    def fake_post(url, *args, **kwargs):
        captured["url"] = url
        captured["body"] = kwargs.get("json")
        canned = {"candidates": [_good("shelter"), _good("beacon"), _good("bridge")]}
        return _FakeResp({"choices": [{"message": {"content": json.dumps(canned)}}]})

    monkeypatch.setattr(ac.requests, "post", fake_post)
    monkeypatch.setenv("IMAGEV2_API_KEY", "sk-test")

    out = ac.author_and_record(
        sess,
        llm_base_url="https://example/v1/chat/completions",
        llm_model="gpt-5.5",
        api_key_env="IMAGEV2_API_KEY",
    )

    # public candidates written + session advanced
    assert out.exists()
    manifest = json.loads((sess / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "candidates_ready"

    # PRIVATE draft preserved
    assert (sess / "private" / "candidate-draft.json").exists()

    # PRIVACY: the request body sent to the LLM must NOT contain raw honeypots
    body_str = json.dumps(captured["body"], ensure_ascii=False)
    assert "1997-08-12" not in body_str, "raw birth_date leaked to drafting LLM"
    assert "23:30" not in body_str, "raw birth_time leaked to drafting LLM"
    assert "Asia/Shanghai" not in body_str, "raw timezone leaked to drafting LLM"
    assert "Chenzhou" not in body_str, "raw place leaked to drafting LLM"
    assert "private_rationale" not in body_str, "private rationale leaked to drafting LLM"
    assert "28.0" not in body_str or "113.0" not in body_str, "coordinates leaked to drafting LLM"

    # and it DID send the deidentified facts (asc_sign etc.)
    assert "Aries" in body_str
    assert "Ashwini" in body_str

    # and the credential was used as a bearer header, not embedded in the body
    assert "sk-test" not in body_str


def test_author_strips_code_fence_from_llm_reply(tmp_path: Path, monkeypatch):
    sess = _chart_ready_session(tmp_path / "session")
    (sess / "private" / "chart" / "pet-profile.json").write_text(
        json.dumps(_profile_with_honeypots()), encoding="utf-8")

    canned = {"candidates": [_good("shelter"), _good("beacon"), _good("bridge")]}

    def fake_post(url, *args, **kwargs):
        # LLM wraps JSON in a code fence — must still parse.
        return _FakeResp({"choices": [{"message": {"content": "```json\n" + json.dumps(canned) + "\n```"}}]})

    monkeypatch.setattr(ac.requests, "post", fake_post)
    monkeypatch.setenv("IMAGEV2_API_KEY", "sk-test")

    out = ac.author_and_record(sess, llm_base_url="https://example/v1/chat/completions",
        llm_model="gpt-5.5", api_key_env="IMAGEV2_API_KEY")
    assert len(json.loads(out.read_text(encoding="utf-8"))["candidates"]) == 3


def test_author_raises_if_api_key_env_missing(tmp_path: Path, monkeypatch):
    sess = _chart_ready_session(tmp_path / "session")
    (sess / "private" / "chart" / "pet-profile.json").write_text(
        json.dumps(_profile_with_honeypots()), encoding="utf-8")
    monkeypatch.delenv("IMAGEV2_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="API key"):
        ac.author_and_record(sess, llm_base_url="https://example/v1/chat/completions",
            llm_model="gpt-5.5", api_key_env="IMAGEV2_API_KEY")
