#!/usr/env/bin python3
"""compute_chart_report.py — the astrology seam for the Vedic Companion IP skill.

Runtime budget for this stage:
    one deterministic local PyJHora/Swiss-Ephemeris computation (via the
    superpowers vedic-calculator engine) -> one private structured chart
    report -> one design-safe evidence projection.

Privacy:
    Birth input is read from a PRIVATE intake file, used for computation, then
    the raw engine dict is dropped. Only the slim VedicChartFacts + sanitized
    provenance are written to ``chart-report.json`` (a PrivateIntake artifact —
    never Git-tracked, never fed to imagegen). Only the de-identified
    DesignSafeEvidence is written to ``pet-profile.json`` (design-safe).

Hard stops (fail closed, never fabricate):
    * missing/ambiguous birth field            -> ask, do not compute
    * engine import / computation failure      -> stop
    * SAV != 337                                -> stop
    * facts incomplete / provenance invalid    -> do not write design-safe

Run with the configured local Vedic runtime so the engine imports resolve:
    "$VEDIC_PY" scripts/compute_chart_report.py \\
        --intake /private/path/to/intake.json \\
        --outdir /private/path/to/session/private/chart
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# Make the contracts module importable when run as a script.
_PKG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PKG_ROOT))
from companion_ip_contract import (  # noqa: E402
    BirthInput, ComputationProvenance, VedicChartFacts, PlanetPosition,
    NakshatraFact, DashaFact, PrivateChartReport, build_design_safe_evidence,
    COMPUTATION_SOURCE, AYANAMSA_SYSTEM, NODE_MODE, SAV_TOTAL_EXPECTED,
    privacy_scan, StepResult,
)

# Engine location — the superpowers vedic-calculator skill.
VEDIC_CALC_SCRIPTS = os.environ.get(
    "VEDIC_CALC_SCRIPTS", str(Path.home() / ".claude/skills/vedic-calculator/scripts")
)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
SEVEN_GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


# --------------------------------------------------------------------------- #
# Engine glue
# --------------------------------------------------------------------------- #

def _load_engine():
    sys.path.insert(0, VEDIC_CALC_SCRIPTS)
    try:
        from engine import calculate_full_chart  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            f"vedic-calculator engine not importable from {VEDIC_CALC_SCRIPTS}: {exc}"
        ) from exc
    return calculate_full_chart


def _engine_versions() -> tuple[str, str]:
    try:
        import swisseph as swe  # type: ignore
        swe_ver = getattr(swe, "version", "unknown")
    except Exception:
        swe_ver = "unknown"
    try:
        import jhora  # type: ignore
        jh_ver = getattr(jhora, "__version__", "unknown")
    except Exception:
        jh_ver = "unknown"
    return str(swe_ver), str(jh_ver)


# --------------------------------------------------------------------------- #
# Projection: rich engine dict -> slim VedicChartFacts
# --------------------------------------------------------------------------- #

def _find_birth_mahadasha(dashas: list[dict], dob_iso: str) -> tuple[str, int, int, int]:
    """Find the mahadasha whose [start,end) contains the birth date.

    dashas entries look like {'planet':'Mars','start':'1990-01','end':'1997-01',...}.
    Returns (lord, balance_years, balance_months, balance_days). If we cannot
    confirm the containing dasha, falls back to dashas[0] and reports 0 balance
    rather than fabricating a precise balance.
    """
    import datetime as dt

    def parse_month(s: str) -> dt.date:
        y, m = s.split("-")[:2]
        return dt.date(int(y), int(m), 1)

    birth = dt.date.fromisoformat(dob_iso)
    for d in dashas:
        try:
            start = parse_month(d["start"])
            end = parse_month(d["end"])
        except (KeyError, ValueError):
            continue
        if start <= birth < end:
            total = (end - start).days
            remaining = (end - birth).days
            bal_years = int(remaining // 365)
            bal_months = int((remaining % 365) // 30)
            bal_days = int(remaining - bal_years * 365 - bal_months * 30)
            return str(d["planet"]), bal_years, bal_months, bal_days
    # Fallback — do not fabricate a balance.
    lord = str(dashas[0].get("planet", "")) if dashas else ""
    return lord, 0, 0, 0


def build_facts_from_engine(chart: dict, dob_iso: str) -> VedicChartFacts:
    """Project the engine's rich dict down to the accepted slim contract.

    Deliberately drops: nakshatra pada, shadbala, divisionals, dense aspects,
    yoga sets, full provenance. We do not claim or fabricate those fields.
    """
    lagna = chart["lagna"]
    asc_sign_name = lagna["sign"]
    asc_sign_index = lagna["sign_idx"]
    asc_longitude = float(lagna.get("longitude", lagna.get("degree", 0.0)))

    planets_out: list[PlanetPosition] = []
    engine_planets = chart["planets"]
    for name in SEVEN_GRAHAS + ["Rahu", "Ketu"]:
        p = engine_planets[name]
        planets_out.append(PlanetPosition(
            planet=name,
            sign_index=int(p["sign_idx"]),
            sign_name=p["sign"],
            longitude_in_sign=float(p.get("degree", 0.0)),
            house_from_asc=int(p["house"]),
            retrograde=bool(p.get("retrograde", False)),
            dignity=str(p.get("dignity", "neutral") or "neutral"),
        ))

    moon_nak = engine_planets["Moon"].get("nakshatra", {})
    nakshatra = NakshatraFact(
        index=int(moon_nak.get("index", 0)) if "index" in moon_nak else _nak_index(moon_nak.get("name", "")),
        name=str(moon_nak.get("name", "")),
        balance_percent=0.0,  # not reliably exposed without fabricating; see dasha balance
    )

    lord, by, bm, bd = _find_birth_mahadasha(chart.get("dashas", []), dob_iso)
    dasha = DashaFact(mahadasha_lord=lord, balance_years=by, balance_months=bm, balance_days=bd)

    # Atmakaraka = graha (Sun..Saturn) with max longitude-in-sign, per the
    # accepted builder. Rahu/Ketu excluded.
    ak = max(
        (p for p in planets_out if p.planet in SEVEN_GRAHAS),
        key=lambda p: p.longitude_in_sign,
        default=planets_out[0],
    )

    return VedicChartFacts(
        ascendant_sign_index=asc_sign_index,
        ascendant_sign_name=asc_sign_name,
        ascendant_longitude=asc_longitude,
        planets=planets_out,
        nakshatra=nakshatra,
        dasha=dasha,
        atmakaraka_planet=ak.planet,
        atmakaraka_sign_name=ak.sign_name,
        computation_source=COMPUTATION_SOURCE,
    )


def _nak_index(name: str) -> int:
    NAMES = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
        "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
        "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
        "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
        "Revati",
    ]
    for i, n in enumerate(NAMES):
        if n.lower() == name.lower():
            return i
    return 0


def _sav_total(chart: dict) -> int:
    return int(sum(chart.get("sav", {}).get(s, 0) for s in SIGNS))


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def load_intake(path: Path) -> BirthInput:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return BirthInput(
        birth_date=raw["birth_date"],
        birth_time=raw["birth_time"],
        birth_place=raw["birth_place"],
        timezone=raw["timezone"],
        lat=float(raw["lat"]),
        lon=float(raw["lon"]),
    )


def _birth_to_engine_kwargs(b: BirthInput) -> dict:
    y, m, d = b.birth_date.split("-")
    hh, mm = b.birth_time.split(":")
    return dict(
        year=int(y), month=int(m), day=int(d),
        hour=int(hh), minute=int(mm),
        lat=b.lat, lon=b.lon, tz_str=b.timezone,
    )


def _write_private(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)


def run(intake_path: Path, outdir: Path) -> list[StepResult]:
    steps: list[StepResult] = []
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. Intake
    birth = load_intake(intake_path)
    missing = birth.missing_fields()
    if missing:
        steps.append(StepResult(False, "intake", f"missing fields: {missing}"))
        return steps
    steps.append(StepResult(True, "intake", "complete birth data"))

    # 2. Compute
    try:
        calc = _load_engine()
        chart = calc(**_birth_to_engine_kwargs(birth))
    except Exception as exc:  # noqa: BLE001
        steps.append(StepResult(False, "compute", f"engine failure: {exc}"))
        return steps

    sav = _sav_total(chart)
    if sav != SAV_TOTAL_EXPECTED:
        steps.append(StepResult(False, "compute",
                               f"SAV={sav} != {SAV_TOTAL_EXPECTED}; aborting before interpretation"))
        return steps
    steps.append(StepResult(True, "compute", f"SAV={sav}; ayanamsa={chart.get('ayanamsa')}"))

    # 3. Provenance
    swe_ver, jh_ver = _engine_versions()
    provenance = ComputationProvenance(
        computation_source=COMPUTATION_SOURCE,
        ayanamsa_system=AYANAMSA_SYSTEM,
        ayanamsa_degrees=float(chart.get("ayanamsa", 0.0)),
        node_mode=NODE_MODE,
        pysweph_version=swe_ver,
        pyjhora_version=jh_ver,
        sav_total=sav,
    )
    if not provenance.is_valid():
        steps.append(StepResult(False, "provenance", "provenance invalid; aborting"))
        return steps
    steps.append(StepResult(True, "provenance", str(provenance)))

    # 4. Facts
    facts = build_facts_from_engine(chart, birth.birth_date)
    if not facts.is_complete() or not facts.has_valid_provenance():
        steps.append(StepResult(False, "facts",
                                f"incomplete facts: planets={sorted(facts.planet_names())}"))
        return steps
    steps.append(StepResult(True, "facts", f"{len(facts.planets)} planets; AK={facts.atmakaraka_planet}"))

    # 5. Private chart report (PrivateIntake — NEVER Git/image/QA)
    report = PrivateChartReport(facts=facts, provenance=provenance)
    chart_path = outdir / "chart-report.json"
    _write_private(chart_path, report.to_json())
    steps.append(StepResult(True, "private_report",
                            f"wrote {chart_path}", report.sha256()))

    # 6. Design-safe evidence (de-identified; what synthesis consumes)
    evidence = build_design_safe_evidence(facts)
    # Final privacy guard on the design-safe artifact.
    ev_blob = json.dumps(evidence.deidentified_facts, ensure_ascii=False)
    clean, findings = privacy_scan(ev_blob)
    if not clean:
        steps.append(StepResult(False, "design_safe",
                                f"privacy scan failed: {findings}"))
        return steps
    profile_path = outdir / "pet-profile.json"
    _write_private(
        profile_path,
        json.dumps({"design_safe_evidence": evidence.__dict__}, ensure_ascii=False, indent=2),
    )
    ev_hash = hashlib.sha256(ev_blob.encode("utf-8")).hexdigest()
    steps.append(StepResult(True, "design_safe", f"wrote {profile_path}", ev_hash))

    # Raw engine dict is dropped here — not persisted, per the privacy boundary.
    del chart
    return steps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intake", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args()

    steps = run(args.intake, args.outdir)
    for s in steps:
        flag = "OK  " if s.ok else "FAIL"
        line = f"[{flag}] {s.stage}: {s.detail}"
        if s.artifact_hash:
            line += f"  sha={s.artifact_hash[:12]}"
        print(line)
    return 0 if all(s.ok for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
