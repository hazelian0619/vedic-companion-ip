"""Regression tests for the adversarially-found privacy-gate bypasses.

Every test here was a confirmed bypass found by the adversarial verification
workflow. The gate must now catch all of them.
"""
from companion_ip_contract import astrology_term_scan, privacy_scan


# ---------- coordinates (was: <3 decimals or non-comma separator bypassed) ---------- #

def test_coord_with_two_decimals_is_caught():
    assert not privacy_scan("centered lotus at bearing 28.23, 113.03")[0]

def test_coord_with_word_separator_is_caught():
    assert not privacy_scan("lat 28.123 by 113.456")[0]

def test_coord_with_labels_is_caught():
    assert not privacy_scan("latitude 28.123 longitude 113.456")[0]


# ---------- dates (was: ISO-only regex bypassed common formats) ---------- #

def test_date_month_name_format_is_caught():
    assert not privacy_scan("born Aug 12 1997")[0]

def test_date_day_month_name_format_is_caught():
    assert not privacy_scan("born 12 August 1997")[0]

def test_date_slash_format_is_caught():
    assert not privacy_scan("born 12/08/1997")[0]

def test_date_iso_still_caught():
    assert not privacy_scan("born 1997-08-12")[0]


# ---------- times (was: colon-only regex bypassed other forms) ---------- #

def test_time_four_digit_is_caught():
    assert not privacy_scan("at 0830")[0]

def test_time_am_pm_is_caught():
    assert not privacy_scan("at 8 AM")[0]

def test_time_dot_is_caught():
    assert not privacy_scan("at 8.30")[0]

def test_time_colon_still_caught():
    assert not privacy_scan("at 08:30")[0]


# ---------- birth-phrase (was: "born at", "birthday", "birth date" space bypassed) ---------- #

def test_born_at_is_caught():
    assert not privacy_scan("born at dawn")[0]

def test_birthday_is_caught():
    assert not privacy_scan("the birthday notch")[0]

def test_birth_date_space_is_caught():
    assert not privacy_scan("the birth date marker")[0]


# ---------- astrology terms: CJK planet names (was: only 行星 listed) ---------- #

def test_chinese_planet_names_are_caught():
    for term in ("土星", "木星", "金星", "水星", "火星"):
        assert astrology_term_scan(f"the {term} rust ring"), f"missed {term}"

def test_traditional_chinese_planet_names_are_caught():
    for term in ("太陽", "太陰", "羅睺", "計都"):
        assert astrology_term_scan(f"the {term} node"), f"missed {term}"

def test_chinese_synonyms_are_caught():
    for term in ("星曜", "大限", "命宫", "命主"):
        assert astrology_term_scan(f"the {term} arc"), f"missed {term}"


# ---------- astrology terms: Korean + Japanese (was: not covered) ---------- #

def test_korean_hangul_planet_names_are_caught():
    for term in ("토성", "목성", "금성", "수성", "화성"):
        assert astrology_term_scan(f"the {term} echo"), f"missed {term}"

def test_japanese_romaji_planet_names_are_caught():
    for term in ("Dosei", "Mokusei", "Kinsei", "Suisei", "Kasei"):
        assert astrology_term_scan(f"the {term} flank"), f"missed {term}"

def test_japanese_kanji_planet_names_are_caught():
    for term in ("土星", "木星"):  # kanji overlap with simplified Chinese
        assert astrology_term_scan(f"the {term} flank"), f"missed {term}"


# ---------- nakshatra names (the LLM saw moon_nakshatra_name; could parrot it) ---------- #

def test_nakshatra_names_are_caught():
    for name in ("Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
                 "Pushya", "Anuradha", "Chitra", "Swati", "Vishakha"):
        assert astrology_term_scan(f"the {name} grain"), f"missed {name}"
