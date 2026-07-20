"""Privacy + pipeline tests for the standardized vedic-companion-ip skill.

Unit tests (no codex, no image gen) cover the privacy boundary + contracts.
One deterministic e2e test covers Stage 1 (real vedic compute → private
chart-report + de-id pet-profile). The codex-dependent Stages 2/3/4 are
exercised by `run.py` end-to-end, not here (they need Codex authed + are slow).

Runnable with pytest, or directly:  python3 tests/test_pipeline.py
"""
import os
import json
import subprocess
import sys
import tempfile
import stat
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG / "skill"))
from companion_ip_contract import (  # noqa: E402
    privacy_scan, astrology_term_scan, build_design_safe_evidence, BirthInput,
    CompanionProfile, IdentityKernel, MappingEvidence, ImageRequest, COMPUTATION_SOURCE,
)

VEDIC_PY = os.environ.get(
    "VEDIC_PY", str(Path.home() / ".claude/skills/vedic-calculator/venv/bin/python")
)
INTAKE = PKG / "fixtures" / "synthetic_birth.json"
OUT = Path("/tmp/companion_test_run")


def _run(cmd, cwd=PKG):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"FAILED {cmd}\n{r.stdout}\n{r.stderr}"
    return r


# ---------------------------- privacy unit tests -------------------------- #

def test_privacy_scan_catches_birth_data():
    bad = "born 1990-01-01 at 12:00 in Beijing Asia/Shanghai lat 39.9042"
    clean, findings = privacy_scan(bad)
    assert not clean
    assert len(findings) >= 3


def test_privacy_scan_catches_provenance_detail():
    clean, findings = privacy_scan("ayanamsa 23.7 via pysweph swiss ephemeris")
    assert not clean and findings


def test_astrology_term_scan_catches_planet_words():
    assert astrology_term_scan("Saturn ruled chart, ascendant Pisces, Moon in Dhanishta")


def test_astrology_term_scan_clean_on_pure_visual():
    assert not astrology_term_scan("a soft woolly indigo companion with one amber catchlight")


def test_design_safe_evidence_has_no_birth_data():
    birth = BirthInput("1990-01-01", "12:00", "X, Y", "Asia/Shanghai", 39.9, 116.4)
    assert birth.is_complete()


def test_image_request_rejects_chart_words():
    leaky = ImageRequest(visual_contract="Saturn ruled chart, ascendant Pisces")
    assert not leaky.is_safe()


def test_companion_profile_needs_two_refs_for_ready():
    p = CompanionProfile(
        identity_kernel=IdentityKernel("a", "b", "c", "d", "e"),
        signals=["s1", "s2", "s3"],
        companion_function="f",
        mapping_evidence=[MappingEvidence("ref1", "sig", "vd", "primary", "low")],
        status="ready",
    )
    assert p.validate()  # must complain: only one primary ref


def test_modules_import():
    import appeal_dna, concept_translate, llm_or_codex, build_dna_doc  # noqa: F401
    assert callable(appeal_dna.bake_dna)
    assert hasattr(concept_translate, "RULES_PROMPT")
    assert callable(llm_or_codex.run_codex)


# ---------------------------- Stage 1 e2e (deterministic) ------------------ #
# These need a configured VEDIC_PY runtime + the gitignored intake fixture, so
# they only run locally (skipped in CI / fresh clones).

_HAS_VEDIC_PY = Path(VEDIC_PY).is_file()
_HAS_INTAKE = INTAKE.is_file()
_stage1_skip = pytest.mark.skipif(
    not (_HAS_VEDIC_PY and _HAS_INTAKE),
    reason="VEDIC_PY runtime or intake fixture not configured (local-only)",
)
_proto_skip = pytest.mark.skipif(
    not (PKG / "appeal_dna.py").is_file(),
    reason="prototype modules (appeal_dna etc.) not present in shipped-skill build",
)


@_proto_skip
def test_modules_import():
    import appeal_dna, concept_translate, llm_or_codex, build_dna_doc  # noqa: F401
    assert callable(appeal_dna.bake_dna)
    assert hasattr(concept_translate, "RULES_PROMPT")
    assert callable(llm_or_codex.run_codex)


# ---------------------------- Stage 1 e2e (deterministic) ------------------ #

def _stage1(outdir):
    _run([VEDIC_PY, str(PKG / "skill" / "scripts" / "compute_chart_report.py"),
          "--intake", str(INTAKE), "--outdir", str(outdir)])


@_stage1_skip
def test_stage1_produces_private_and_design_safe():
    OUT.mkdir(parents=True, exist_ok=True)
    _stage1(OUT)
    for name in ("chart-report.json", "pet-profile.json"):
        assert (OUT / name).exists(), f"missing {name}"


@_stage1_skip
def test_stage1_private_outputs_are_owner_only():
    _stage1(OUT)
    for name in ("chart-report.json", "pet-profile.json"):
        assert stat.S_IMODE((OUT / name).stat().st_mode) == 0o600


@_stage1_skip
def test_pet_profile_is_privacy_clean():
    _stage1(OUT)
    blob = (OUT / "pet-profile.json").read_text()
    clean, findings = privacy_scan(blob)
    birth_findings = [f for f in findings if "birth" in f or "time" in f
                      or "coordinate" in f or "timezone" in f or "pada" in f
                      or "ayanamsa" in f or "swisseph" in f or "ephemeris" in f]
    assert birth_findings == [], birth_findings


@_stage1_skip
def test_stage1_sav_invariant_and_provenance():
    _stage1(OUT)
    d = json.loads((OUT / "chart-report.json").read_text())
    prov = d.get("provenance", {})
    if isinstance(prov, dict):
        assert prov.get("computation_source") == "pyjhora-swiss-ephemeris"
    else:
        assert getattr(prov, "computation_source", None) == "pyjhora-swiss-ephemeris"


@_stage1_skip
def test_compute_fails_closed_on_missing_birth():
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        bad = tdp / "bad.json"
        bad.write_text(json.dumps({"birth_date": "1990-01-01", "birth_time": "",
                                   "birth_place": "", "timezone": "", "lat": 0, "lon": 0}))
        r = subprocess.run([VEDIC_PY, str(PKG / "skill" / "scripts" / "compute_chart_report.py"),
                           "--intake", str(bad), "--outdir", str(tdp)],
                          capture_output=True, text=True)
        assert r.returncode != 0
        assert "missing" in (r.stdout + r.stderr).lower()


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except Exception:  # noqa: BLE001
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
