from __future__ import annotations

import json
from pathlib import Path

from scripts.prepare_candidate_runs import prepare_candidate_runs
from scripts.record_candidate_bases import record_candidate_bases
from session_contract import ProductSession


def _candidate(candidate_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "ip_name": f"{candidate_id.title()} Companion",
        "display_name": f"{candidate_id.title()} / Direction",
        "description": "A compact companion with one distinct, protected feature.",
        "form_metaphor": "A compact form with one protected central signal.",
        "silhouette_tokens": ["compact silhouette", "stable lower mass"],
        "palette_tokens": ["dominant resting field", "one contained living accent"],
        "material_tokens": ["layered tactile outer shell", "matte inner surface"],
        "signature_hook": "One protected core integrated at the body center.",
        "anti_drift": ["no scenery", "no generic blob"],
    }


def _candidates_ready_session(tmp_path: Path) -> ProductSession:
    session = ProductSession.create(tmp_path / "session")
    chart = session.write_public("chart-ready.json", {})
    session.transition("chart_ready", artifact_paths=[chart], decision="computed")
    candidates = session.write_public(
        "safe-candidates.json",
        {"candidates": [_candidate(candidate_id) for candidate_id in ("a", "b", "c")]},
    )
    session.transition("candidates_ready", artifact_paths=[candidates], decision="compiled")
    return session


def test_prepare_candidate_runs_records_three_session_owned_official_runs(tmp_path: Path, monkeypatch):
    session = _candidates_ready_session(tmp_path)

    def fake_prepare(candidate: dict, output_dir: Path, hatch_pet_dir: Path, force: bool) -> Path:
        run = output_dir / candidate["candidate_id"] / "hatch-pet-run"
        run.mkdir(parents=True)
        (run / "imagegen-jobs.json").write_text(json.dumps({"jobs": []}), encoding="utf-8")
        (run / "pet_request.json").write_text(json.dumps({"pet_id": candidate["candidate_id"]}), encoding="utf-8")
        return run

    monkeypatch.setattr("scripts.prepare_candidate_runs.prepare_run", fake_prepare)

    manifest_path = prepare_candidate_runs(session.root, hatch_pet_dir=tmp_path / "hatch-pet")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [entry["candidate_id"] for entry in manifest["candidates"]] == ["a", "b", "c"]
    assert all(not Path(entry["hatch_run_dir"]).is_absolute() for entry in manifest["candidates"])
    assert json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"] == "candidate_runs_ready"


def test_record_candidate_bases_accepts_only_the_three_prepared_session_runs(tmp_path: Path):
    session = _candidates_ready_session(tmp_path)
    runs = []
    bases_by_candidate = {}
    for candidate_id in ("a", "b", "c"):
        run = session.root / "candidate-runs" / candidate_id / "hatch-pet-run"
        base = run / "references" / "canonical-base.png"
        base.parent.mkdir(parents=True)
        base.write_bytes(f"base-{candidate_id}".encode("utf-8"))
        (run / "imagegen-jobs.json").write_text(
            json.dumps({"jobs": [{"id": "base", "status": "complete"}]}),
            encoding="utf-8",
        )
        (run / "pet_request.json").write_text(json.dumps({"pet_id": candidate_id}), encoding="utf-8")
        runs.append({"candidate_id": candidate_id, "hatch_run_dir": str(run.relative_to(session.root))})
        bases_by_candidate[candidate_id] = base
    run_manifest = session.write_public("candidate-runs.json", {"version": 1, "candidates": runs})
    session.transition("candidate_runs_ready", artifact_paths=[run_manifest], decision="prepared")

    bases_manifest = record_candidate_bases(session.root, bases_by_candidate, reviewer="visual-agent", note="all three bases accepted")

    payload = json.loads(bases_manifest.read_text(encoding="utf-8"))
    assert [entry["candidate_id"] for entry in payload["bases"]] == ["a", "b", "c"]
    assert all(entry["base_sha256"] for entry in payload["bases"])
    assert json.loads((session.root / "session.json").read_text(encoding="utf-8"))["state"] == "candidate_bases_ready"


def test_record_candidate_bases_rejects_a_base_outside_its_recorded_hatch_run(tmp_path: Path):
    session = _candidates_ready_session(tmp_path)
    runs = []
    bases_by_candidate = {}
    for candidate_id in ("a", "b", "c"):
        run = session.root / "candidate-runs" / candidate_id / "hatch-pet-run"
        (run / "references").mkdir(parents=True)
        (run / "imagegen-jobs.json").write_text(
            json.dumps({"jobs": [{"id": "base", "status": "complete"}]}),
            encoding="utf-8",
        )
        (run / "pet_request.json").write_text(json.dumps({"pet_id": candidate_id}), encoding="utf-8")
        base = run / "references" / "canonical-base.png"
        base.write_bytes(f"base-{candidate_id}".encode("utf-8"))
        runs.append({"candidate_id": candidate_id, "hatch_run_dir": str(run.relative_to(session.root))})
        bases_by_candidate[candidate_id] = base
    outside_base = session.root / "untracked-base.png"
    outside_base.write_bytes(b"wrong-base")
    bases_by_candidate["b"] = outside_base
    run_manifest = session.write_public("candidate-runs.json", {"version": 1, "candidates": runs})
    session.transition("candidate_runs_ready", artifact_paths=[run_manifest], decision="prepared")

    try:
        record_candidate_bases(session.root, bases_by_candidate, reviewer="visual-agent", note="all three bases accepted")
    except ValueError as error:
        assert "recorded Hatch run" in str(error)
    else:
        raise AssertionError("untracked bases must not enter the Character Bible stage")
