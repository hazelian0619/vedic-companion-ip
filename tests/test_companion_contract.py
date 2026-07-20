"""Tests for the hardened privacy contract: whole-word scan, Chinese denylist, schema whitelist."""
from companion_ip_contract import (
    astrology_term_scan,
    privacy_scan,
    CANDIDATE_SCHEMA_FIELDS,
    validate_candidate_schema,
)


# ---------------- whole-word scan (English) ---------------- #

def test_whole_word_scan_does_not_false_positive_on_sunflower():
    assert "Sun" not in astrology_term_scan("a sunflower in the garden")


def test_whole_word_scan_does_not_false_positive_on_sunday():
    assert "Sun" not in astrology_term_scan("see you on sunday")


def test_whole_word_scan_catches_bare_sun():
    assert "Sun" in astrology_term_scan("the Sun shines bright")


def test_whole_word_scan_catches_saturn_not_saturnine():
    assert "Saturn" in astrology_term_scan("ruled by Saturn")
    assert "Saturn" not in astrology_term_scan("a saturnine mood")


def test_whole_word_scan_catches_house_only_as_bare_word():
    # "household" must not trip "house"; bare "house" should.
    assert "house" not in astrology_term_scan("a household companion")
    assert "house" in astrology_term_scan("the first house of the chart")


# ---------------- Chinese astrology denylist ---------------- #

def test_chinese_astrology_terms_are_caught():
    found = astrology_term_scan("这只角色的行星落在月亮与上升")
    assert "行星" in found
    assert "月亮" in found
    assert "上升" in found


def test_chinese_dasha_and_nakshatra_terms_are_caught():
    found = astrology_term_scan("当前大运由月亮星宿主导")
    assert found  # at least one Chinese term


# ---------------- schema whitelist ---------------- #

def test_schema_whitelist_rejects_unknown_field():
    cand = {"candidate_id": "x", "ip_name": "X", "bogus_field": "leak"}
    errs = validate_candidate_schema(cand)
    assert "bogus_field" in errs


def test_schema_whitelist_rejects_multiple_unknown_fields():
    cand = {"candidate_id": "x", "a": 1, "b": 2, "ip_name": "X"}
    errs = validate_candidate_schema(cand)
    assert "a" in errs and "b" in errs


def test_schema_whitelist_accepts_clean_candidate():
    cand = {f: "v" for f in CANDIDATE_SCHEMA_FIELDS}
    assert validate_candidate_schema(cand) == []


def test_schema_whitelist_fields_match_contract():
    # Must match the portable character-bible-contract.md schema exactly.
    assert CANDIDATE_SCHEMA_FIELDS == frozenset({
        "candidate_id", "ip_name", "display_name", "description",
        "form_metaphor", "silhouette_tokens", "palette_tokens",
        "material_tokens", "signature_hook", "interaction_signature",
        "board_composition", "anti_drift",
    })


# ---------------- privacy_scan still works (regression) ---------------- #

def test_privacy_scan_still_catches_dates_and_coords():
    clean, findings = privacy_scan("born 1997-08-12 at 23:30 lat 28.0,113.0")
    assert not clean
    assert findings
