"""Typed contracts for the Vedic Companion IP skill.

This module collapses P1-001 (DesignSafeEvidence) and P1-002 (typed
CompanionProfile / VisualCanon) into one self-contained, stdlib-only module.
It deliberately imports nothing from ``persona-compiler`` so it stays runnable
without that codebase's (currently broken) import chain.

Privacy boundary (non-negotiable):
  * Raw birth inputs (date, time, place, coordinates, timezone) live ONLY on
    ``BirthInput`` inside ``PrivateIntake``. They are not persisted by default
    and are deleted after private computation.
  * Only de-identified facts + opaque ``evidence_refs`` may enter
    ``DesignSafeEvidence``.
  * The image model receives only the short, de-identified ``ImageRequest``.
  * ``privacy_scan`` is the hard gate before any artifact leaves the private
    boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any

# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #

#: The accepted computation-source string. Accurate for the vedic-calculator
#: engine: pysweph (Swiss Ephemeris C binding) does the astronomy; PyJHora
#: does ashtakavarga / dasha / shadbala / divisional charts.
COMPUTATION_SOURCE = "pyjhora-swiss-ephemeris"

#: The vedic-calculator engine uses True Chitrapaksha (a Lahiri-family
#: ayanamsa) and Mean Node. These are fixed by the engine, not by us.
AYANAMSA_SYSTEM = "True Chitrapaksha (TRUE_CITRA)"
NODE_MODE = "Mean Node"

#: SAV total for a correctly computed Rasi chart. Hard invariant.
SAV_TOTAL_EXPECTED = 337


@dataclass
class ComputationProvenance:
    """Sanitized provenance. Carries NO birth data, coordinates, or place."""

    computation_source: str
    ayanamsa_system: str
    ayanamsa_degrees: float
    node_mode: str
    pysweph_version: str
    pyjhora_version: str
    sav_total: int

    def is_valid(self) -> bool:
        return (
            self.computation_source == COMPUTATION_SOURCE
            and self.ayanamsa_system == AYANAMSA_SYSTEM
            and self.node_mode == NODE_MODE
            and self.sav_total == SAV_TOTAL_EXPECTED
        )


# --------------------------------------------------------------------------- #
# PrivateIntake — raw birth (NEVER persisted by default, NEVER design-safe)
# --------------------------------------------------------------------------- #

@dataclass
class BirthInput:
    birth_date: str   # YYYY-MM-DD
    birth_time: str    # HH:MM 24h
    birth_place: str   # "City, Country"
    timezone: str      # IANA tz, e.g. "Asia/Shanghai"
    lat: float
    lon: float

    _REQUIRED = ("birth_date", "birth_time", "birth_place", "timezone", "lat", "lon")

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        for name in self._REQUIRED:
            val = getattr(self, name)
            if val in (None, "", ""):
                missing.append(name)
        # coordinate sanity
        if not (-90.0 <= self.lat <= 90.0):
            missing.append("lat_out_of_range")
        if not (-180.0 <= self.lon <= 180.0):
            missing.append("lon_out_of_range")
        return missing

    def is_complete(self) -> bool:
        return not self.missing_fields()


# --------------------------------------------------------------------------- #
# VedicChartFacts — slim, design-safe-compatible (matches accepted contract)
# --------------------------------------------------------------------------- #
# Deliberately drops: nakshatra pada, full provenance, yoga sets, shadbala,
# dense aspects, divisional charts. Do not claim or fabricate those fields.

@dataclass
class PlanetPosition:
    planet: str
    sign_index: int
    sign_name: str
    longitude_in_sign: float
    house_from_asc: int
    retrograde: bool = False
    dignity: str = "neutral"


@dataclass
class NakshatraFact:
    index: int
    name: str
    balance_percent: float
    # NO pada field — accepted contract drops it.


@dataclass
class DashaFact:
    mahadasha_lord: str
    balance_years: int = 0
    balance_months: int = 0
    balance_days: int = 0


@dataclass
class VedicChartFacts:
    ascendant_sign_index: int
    ascendant_sign_name: str
    ascendant_longitude: float
    planets: list[PlanetPosition]
    nakshatra: NakshatraFact
    dasha: DashaFact
    atmakaraka_planet: str = ""
    atmakaraka_sign_name: str = ""
    computation_source: str = COMPUTATION_SOURCE

    REQUIRED_PLANETS = {
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
        "Rahu", "Ketu",
    }

    def planet_names(self) -> set[str]:
        return {p.planet for p in self.planets}

    def is_complete(self) -> bool:
        return self.REQUIRED_PLANETS.issubset(self.planet_names())

    def has_valid_provenance(self) -> bool:
        return self.computation_source == COMPUTATION_SOURCE


# --------------------------------------------------------------------------- #
# Private chart report — the user's PRIVATE artifact (PrivateIntake).
# Never enters Git, design-safe, image prompts, or QA.
# --------------------------------------------------------------------------- #

@dataclass
class PrivateChartReport:
    facts: VedicChartFacts
    provenance: ComputationProvenance
    # NOTE: the full raw engine output is intentionally NOT retained here.
    # It is computed, used to build `facts` + `provenance`, then dropped.

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# DesignSafeEvidence — de-identified; what synthesis consumes.
# --------------------------------------------------------------------------- #

@dataclass
class DesignSafeEvidence:
    """De-identified chart facts expressed as opaque evidence refs.

    No raw birth data, coordinates, place, timezone, nakshatra pada, or
    provenance beyond the sanitized computation_source. Synthesis reads
    evidence_refs + deidentified_facts; it never sees PrivateChartReport.
    """

    evidence_refs: list[str]
    deidentified_facts: dict[str, Any]
    computation_source: str = COMPUTATION_SOURCE
    provenance_sanitized: bool = True

    def ref(self, key: str) -> Any:
        return self.deidentified_facts.get(key)


def build_design_safe_evidence(facts: VedicChartFacts) -> DesignSafeEvidence:
    """Project a private VedicChartFacts down to a de-identified evidence set.

    Keeps: ascendant sign name, each planet's sign + house + retrograde +
    dignity, nakshatra name (NOT pada), dasha mahadasha lord, atmakaraka.
    Drops: all numeric longitudes (fingerprintable), balance percentages,
    coordinates, place, dates, times, pada, divisionals, shadbala.
    """
    deid: dict[str, Any] = {
        "asc_sign": facts.ascendant_sign_name,
        "planets": {
            p.planet: {
                "sign": p.sign_name,
                "house": p.house_from_asc,
                "retrograde": p.retrograde,
                "dignity": p.dignity,
            }
            for p in facts.planets
        },
        "moon_nakshatra_name": facts.nakshatra.name,
        "mahadasha_lord": facts.dasha.mahadasha_lord,
        "atmakaraka": facts.atmakaraka_planet,
    }
    refs = [f"asc_sign:{facts.ascendant_sign_name}"]
    for p in facts.planets:
        refs.append(f"planet:{p.planet}:sign:{p.sign_name}:house:{p.house_from_asc}")
    refs.append(f"nakshatra_name:{facts.nakshatra.name}")
    refs.append(f"mahadasha:{facts.dasha.mahadasha_lord}")
    refs.append(f"atmakaraka:{facts.atmakaraka_planet}")
    return DesignSafeEvidence(
        evidence_refs=refs,
        deidentified_facts=deid,
        computation_source=facts.computation_source,
        provenance_sanitized=True,
    )


# --------------------------------------------------------------------------- #
# CompanionProfile (P1-002) + mapping evidence
# --------------------------------------------------------------------------- #

SIGNAL_MIN = 3
SIGNAL_MAX = 5


@dataclass
class IdentityKernel:
    """Stable across reruns. Pose/light/microtexture may vary; these may not."""
    species_family: str
    primary_silhouette: str
    palette_relationship: str
    signature_object: str
    companion_function: str


@dataclass
class MappingEvidence:
    evidence_ref: str        # links back into DesignSafeEvidence.evidence_refs
    signal: str              # personality/regulation signal
    visual_decision: str
    weight: str = "secondary"        # "primary" | "secondary"
    uncertainty: str = "medium"      # "low" | "medium" | "high"


@dataclass
class CompanionProfile:
    identity_kernel: IdentityKernel
    signals: list[str]
    companion_function: str
    mapping_evidence: list[MappingEvidence]
    status: str = "needs-review"      # "ready" | "needs-review"

    def is_ready(self) -> bool:
        return self.status == "ready"

    def validate(self) -> list[str]:
        """Return list of contract violations (empty == valid)."""
        errs: list[str] = []
        if not (SIGNAL_MIN <= len(self.signals) <= SIGNAL_MAX):
            errs.append(f"signals count {len(self.signals)} not in [{SIGNAL_MIN},{SIGNAL_MAX}]")
        if not self.mapping_evidence:
            errs.append("mapping_evidence empty")
        # major identity decisions need >=2 independent evidence refs
        primary_refs = {
            m.evidence_ref for m in self.mapping_evidence if m.weight == "primary"
        }
        if len(primary_refs) < 2 and self.status == "ready":
            errs.append("major identity decision has fewer than two evidence refs")
        # every mapping ref must resolve against evidence
        return errs


# --------------------------------------------------------------------------- #
# VisualCanon — typed visual contract
# --------------------------------------------------------------------------- #

@dataclass
class VisualCanon:
    """Layered visual contract, mirroring the Ye Pan PetAestheticTemplate +
    YepanPetReading structure, but with a NON-Ye-Pan palette identity.

    Richness is NOT a privacy risk: every field is a de-identified, translated
    token. No planet/sign/nakshatra/chart words reach the image model.
    """
    # core identity
    name: str                          # coined pet name (deterministic)
    display_name: str                  # localized name
    subject_archetype: str
    # layered tokens (what the image model + board legend consume)
    silhouette_tokens: list[str]
    palette_tokens: list[str]
    material_tokens: list[str]
    charm_tokens: list[str]
    signature_hook: str
    signature_points: list[str]
    form_metaphor: str                 # central poetic object
    visual_role: str
    material_tension: str              # specific material contrast
    composition_rules: str
    negative_drift: list[str]          # actionable anti-drift for the image model
    anti_drift: list[str]              # IP-level anti-drift (board footer)
    # flat legacy fields (kept for the board renderer + tests)
    species_family: str = ""
    proportions: str = ""
    material: str = ""
    palette_roles: dict = field(default_factory=dict)
    face_rules: dict = field(default_factory=dict)
    signature_object: str = ""
    silhouette_hook: str = ""
    forbidden_shortcuts: tuple = (
        "one planet -> one color",
        "one sign -> one animal",
        "one nakshatra -> one prop",
        "image model reads chart dump / private report / fable / essay",
    )


# --------------------------------------------------------------------------- #
# ImageRequest — the ONLY thing the image model receives. De-identified.
# --------------------------------------------------------------------------- #

# Patterns that must NEVER appear in an image request / public artifact.
# Broadened after adversarial verification found ISO-only date, colon-only time,
# 3-decimal-comma-only coord, and "born at"/"birthday"/"birth date"(space) bypasses.
# Design vocabulary never contains dates, times, coordinates, or birth framing, so
# erring toward catching more is safe (fail-closed rejects + regenerate).
_PRIVATE_PATTERNS = [
    # --- dates: ISO, slash, month-name (both orders) ---
    (re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b"), "raw birth date (ISO)"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"), "raw birth date (slash D/M/Y)"),
    (re.compile(r"\b\d{4}/\d{1,2}/\d{1,2}\b"), "raw birth date (slash Y/M/D)"),
    (re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b", re.IGNORECASE), "raw birth date (month-name)"),
    (re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b", re.IGNORECASE), "raw birth date (day month-name)"),
    # --- times: colon, 4-digit HHMM, AM/PM, dot ---
    (re.compile(r"\b\d{1,2}:\d{2}\b"), "raw birth time (colon)"),
    (re.compile(r"\b(?:[01]\d|2[0-3])[0-5]\d\b"), "raw birth time (HHMM)"),
    (re.compile(r"\b\d{1,2}\s*[ap]\.?m\.?\b", re.IGNORECASE), "raw birth time (AM/PM)"),
    (re.compile(r"\b\d{1,2}\.\d{2}\b"), "raw birth time (dot)"),
    # --- coordinates: 2+-decimal comma pair, word/separator pair, or lat/lon labels ---
    (re.compile(r"-?\d{1,3}\.\d{2,},\s*-?\d{1,3}\.\d{2,}"), "lat/lon coordinates"),
    (re.compile(r"-?\d{1,3}\.\d+\s*(?:by|/|x)\s*-?\d{1,3}\.\d+", re.IGNORECASE), "lat/lon coordinates (word sep)"),
    (re.compile(r"\blat(?:itude)?\s*[-\d.]+", re.IGNORECASE), "latitude label"),
    (re.compile(r"\blon(?:gitude)?\s*[-\d.]+", re.IGNORECASE), "longitude label"),
    # --- IANA timezone + nakshatra pada ---
    (re.compile(r"\b(?:Asia|Europe|America|Africa|Pacific|Arctic|Atlantic|Indian)/[A-Za-z_]+"), "IANA timezone"),
    (re.compile(r"\bpada\b", re.IGNORECASE), "nakshatra pada"),
    # --- birth-input references: underscore, space, "born at/on/in", birthday ---
    (re.compile(r"\bbirth[_ ]?(?:date|time|place)\b", re.IGNORECASE), "birth input reference"),
    (re.compile(r"\bbirth(?:place|day)\b", re.IGNORECASE), "birth input reference"),
    (re.compile(r"\bborn\s+(?:at|on|in)\b", re.IGNORECASE), "birth input reference"),
    # The design-safe envelope legitimately carries the computation_source
    # label "pyjhora-swiss-ephemeris"; what must NEVER reach image prompts is
    # provenance DETAIL (ayanamsa degrees, engine-internal names). Note
    # "swisseph"/"pysweph" (no dash) do not match the allowed
    # "swiss-ephemeris" (with dash) computation_source string.
    (re.compile(r"(?i)ayanamsa|pysweph|swisseph"), "provenance detail leak"),
]


def privacy_scan(text: str) -> tuple[bool, list[str]]:
    """Return (clean, findings). clean==True means text is design-safe."""
    findings: list[str] = []
    for pat, label in _PRIVATE_PATTERNS:
        m = pat.search(text)
        if m:
            findings.append(f"{label}: '{m.group(0)}'")
    return (len(findings) == 0, findings)


# Words the IMAGE MODEL may never see — reading chart logic / planet names /
# signs would let the model shortcut from the chart instead of the resolved
# visual. The board (a human artifact) MAY use these; the image request MAY NOT.
ASTROLOGY_TERMS = (
    "Saturn", "Jupiter", "Mars", "Venus", "Mercury", "Sun", "Moon", "Rahu", "Ketu",
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces", "nakshatra", "dasha",
    "atmakaraka", "ascendant", "chart", "horoscope", "jyotish", "vedic",
    "house", "retrograde", "mahadasha", "planet", "graha", "rasi",
    # Nakshatra names (the LLM saw moon_nakshatra_name; could parrot it):
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
    # Japanese romaji planet names (Dosei=Saturn, Mokusei=Jupiter, Kinsei=Venus,
    # Suisei=Mercury, Kasei=Mars) + Sun/Moon — ASCII, so the script-range
    # catch-all below does NOT cover them; enumerate explicitly.
    "Dosei", "Mokusei", "Kinsei", "Suisei", "Kasei", "Taiyou", "Taiyo", "Getsu",
)

#: Chinese astrology vocabulary that must never reach an image request or a
#: public candidate. Enumerated for explicit reporting; the East-Asian script
#: catch-all in astrology_term_scan is the comprehensive CJK/Hangul/kana defense.
CHINESE_ASTROLOGY_TERMS = (
    # generic
    "行星", "月亮", "太阳", "星座", "宫位", "上升", "大运", "星宿",
    "劫", "罗睺", "计都", "分盘", "飞星", "命主", "度数", "相位", "落宫",
    # specific planet names — simplified (the actual planet names, not just 行星)
    "土星", "木星", "金星", "水星", "火星", "天王星", "海王星", "冥王星",
    "日", "月",
    # traditional (used in traditional Chinese, Taiwanese, Japanese kanji contexts)
    "太陽", "太陰", "羅睺", "計都",
    # synonyms
    "星曜", "大限", "命宫",
)

#: East-Asian script ranges. Candidates are ALL-English by product rule, so ANY
#: CJK ideograph / Hangul / kana character in a candidate is a leak signal.
#: This catch-all makes CJK coverage complete regardless of the enumerated
#: CHINESE_ASTROLOGY_TERMS list (which can never be exhaustive). Latin Extended
#: (e.g. the ä in "minä perhonen") is NOT in these ranges, so it is not flagged.
_EAST_ASIAN_SCRIPT_RANGES = (
    (0x3400, 0x4DBF),   # CJK Extension A
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0x3040, 0x309F),   # Hiragana
    (0x30A0, 0x30FF),   # Katakana
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0x1100, 0x11FF),   # Hangul Jamo
)


def _has_east_asian_script(text: str) -> str | None:
    """Return the first East-Asian script char in text, or None."""
    for ch in text:
        o = ord(ch)
        for lo, hi in _EAST_ASIAN_SCRIPT_RANGES:
            if lo <= o <= hi:
                return ch
    return None


def astrology_term_scan(text: str) -> list[str]:
    """Return astrology terms found in ``text``.

    English terms match whole-word (case-insensitive) so ``Sun`` does not
    false-trip on ``sunflower``/``sunday`` and ``Saturn`` does not trip
    ``saturnine``. Chinese terms match by substring. Any East-Asian script
    character (CJK/kanji, Hangul, hiragana, katakana) is flagged — candidates
    are English-only, so any such character is a leak signal (this makes CJK
    coverage exhaustive, not dependent on an enumerated list). Japanese romaji
    planet names + nakshatra names are enumerated in ASTROLOGY_TERMS since they
    are ASCII and thus not caught by the script-range check.
    """
    low = text.lower()
    found: list[str] = []
    for term in ASTROLOGY_TERMS:
        if re.search(rf"\b{re.escape(term.lower())}\b", low):
            found.append(term)
    for term in CHINESE_ASTROLOGY_TERMS:
        if term in text:
            found.append(term)
    ea = _has_east_asian_script(text)
    if ea:
        found.append(f"<east-asian-script:{ea}>")
    return found


#: The portable candidate schema (references/character-bible-contract.md). A
#: candidate may contain ONLY these fields. ``validate_candidate_schema``
#: rejects anything outside this whitelist — this is the hard shape boundary
#: for LLM-authored candidate output.
CANDIDATE_SCHEMA_FIELDS = frozenset({
    "candidate_id", "ip_name", "display_name", "description",
    "form_metaphor", "silhouette_tokens", "palette_tokens",
    "material_tokens", "signature_hook", "interaction_signature",
    "board_composition", "anti_drift",
})


def validate_candidate_schema(candidate: dict) -> list[str]:
    """Return unknown-field violations (empty list == schema-clean).

    A candidate carrying any field outside ``CANDIDATE_SCHEMA_FIELDS`` is
    rejected. This whitelist bounds what an LLM-authored candidate may carry,
    so a drafting model cannot smuggle rationale, evidence, or chart refs into
    a public candidate under a novel field name.
    """
    if not isinstance(candidate, dict):
        return ["<not-a-dict>"]
    return sorted(set(candidate) - CANDIDATE_SCHEMA_FIELDS)


@dataclass
class ImageRequest:
    visual_contract: str   # de-identified visual brief (rich, tokenized)
    canon: VisualCanon | None = None  # structured canon (optional; not sent to model)
    canvas: str = "1024x1024"  # canonical base image canvas

    def privacy_scan(self) -> tuple[bool, list[str]]:
        # The image model receives ONLY visual_contract — not the structured
        # canon (the canon feeds the human-facing board legend, which may
        # legitimately name astrology concepts in its rule text). So we scan
        # only the text the model actually sees.
        text = self.visual_contract
        clean, findings = privacy_scan(text)
        leaked = astrology_term_scan(text)
        for t in leaked:
            findings.append(f"astrology term in image request: '{t}'")
        return (len(findings) == 0, findings)

    def is_safe(self) -> bool:
        clean, _ = self.privacy_scan()
        return clean


# --------------------------------------------------------------------------- #
# Hard-stop result envelope (so scripts fail closed, never fabricate)
# --------------------------------------------------------------------------- #

@dataclass
class StepResult:
    ok: bool
    stage: str
    detail: str = ""
    artifact_hash: str = ""    # sha256 of any preserved safe artifact
    # When ok is False, downstream stages MUST NOT run.
