from __future__ import annotations

import json
import stat
from pathlib import Path

from scripts.prepare_product_session import prepare_session, run_private_compute
from session_contract import ProductSession


def test_session_keeps_private_ledger_owner_only_and_public_manifest_safe(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    private = session.write_private("lineage.json", {"evidence_refs": ["private:one"]})
    public = session.write_public("session.json", {"session_id": session.session_id, "state": "intake_ready"})

    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    assert stat.S_IMODE(public.stat().st_mode) == 0o644
    assert "evidence_refs" not in public.read_text(encoding="utf-8")


def test_session_records_hashed_state_transitions(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    artifact = session.write_public("safe-candidates.json", {"candidates": []})

    session.transition("candidates_ready", artifact_paths=[artifact], decision="compiled")

    manifest = json.loads((tmp_path / "run" / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "candidates_ready"
    assert manifest["events"][0]["artifact_hashes"]["safe-candidates.json"]


def test_session_records_a_hashed_public_audit_event_without_changing_state(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    artifact = session.write_public("provenance.json", {"source": "legacy-board-system"})

    session.record_event("provenance_correction", artifact_paths=[artifact], decision="corrected public board provenance")

    manifest = json.loads((tmp_path / "run" / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "intake_ready"
    assert manifest["events"][-1]["kind"] == "provenance_correction"
    assert manifest["events"][-1]["artifact_hashes"]["provenance.json"]


def test_session_can_record_prepared_candidate_runs_before_any_base_exists(tmp_path: Path):
    session = ProductSession.create(tmp_path / "run")
    candidates = session.write_public("safe-candidates.json", {"candidates": []})
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    runs = session.write_public("candidate-runs.json", {"candidates": []})

    session.transition("candidate_runs_ready", artifact_paths=[runs], decision="official runs prepared")

    manifest = json.loads((tmp_path / "run" / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "candidate_runs_ready"


def test_prepare_session_compiles_candidates_from_private_profile(tmp_path: Path):
    intake = tmp_path / "intake.json"
    intake.write_text("{}", encoding="utf-8")

    def fake_compute(_intake: Path, outdir: Path):
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "chart-report.json").write_text("{}", encoding="utf-8")
        (outdir / "pet-profile.json").write_text(
            json.dumps(
                {
                    "design_safe_evidence": {
                        "evidence_refs": ["asc_sign:Aries", "planet:Sun:sign:Leo:house:10"],
                        "deidentified_facts": {
                            "asc_sign": "Aries",
                            "planets": {"Sun": {"sign": "Leo", "house": 10}},
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        return True

    result = prepare_session(intake, tmp_path / "run", compute_fn=fake_compute)

    assert result.candidates_path.is_file()
    assert stat.S_IMODE((tmp_path / "run" / "private" / "chart" / "chart-report.json").stat().st_mode) == 0o600
    manifest = json.loads((tmp_path / "run" / "session.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "candidates_ready"


def test_private_compute_runs_the_configured_vedic_python(monkeypatch, tmp_path: Path):
    seen = {}

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **_kwargs):
        seen["command"] = command
        return Result()

    monkeypatch.setattr("scripts.prepare_product_session.subprocess.run", fake_run)
    vedic_python = tmp_path / "vedic-python"
    vedic_python.write_text("", encoding="utf-8")

    assert run_private_compute(tmp_path / "intake.json", tmp_path / "out", vedic_python=vedic_python) is True
    assert seen["command"][0] == str(vedic_python)
    assert seen["command"][1].endswith("scripts/compute_chart_report.py")
