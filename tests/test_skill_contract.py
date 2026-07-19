"""Contract tests for the portable astro companion Skill."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skill"


def _safe_candidate(candidate_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "ip_name": f"Companion {candidate_id}",
        "display_name": f"Companion {candidate_id}",
        "description": "A compact, tactile companion with one warm focal detail.",
        "form_metaphor": "A small crafted lantern-vessel.",
        "silhouette_tokens": ["compact rounded body", "small stable feet"],
        "palette_tokens": ["smoked teal", "warm ivory", "single amber accent"],
        "material_tokens": ["felted fiber", "matte ceramic"],
        "signature_hook": "One inset amber bead at the chest.",
        "anti_drift": ["no text", "no logos", "no scenery"],
    }


def test_skill_declares_official_hatch_then_imagev2_sequence():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "hatch-pet" in text
    assert "imagev2" in text
    assert "three official hatch-pet canonical bases -> three imagev2 character bibles" in text
    assert "legacy budget-preview path only" in text
    assert "only the selected candidate" in text
    assert "python3 \"$skill_dir/scripts/prepare_product_session.py\"" in text
    assert "scripts/selected_hatch_run.py" in text


def test_preparer_creates_three_official_runs_without_generating_images(tmp_path: Path):
    candidates = tmp_path / "safe-candidates.json"
    candidates.write_text(
        json.dumps({"candidates": [_safe_candidate("a"), _safe_candidate("b"), _safe_candidate("c")]}, indent=2),
        encoding="utf-8",
    )
    output_dir = tmp_path / "runs"
    script = SKILL_DIR / "scripts" / "prepare_candidate_runs.py"
    result = subprocess.run(
        [sys.executable, str(script), "--candidates", str(candidates), "--output-dir", str(output_dir)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    manifest = json.loads((output_dir / "candidate-runs.json").read_text(encoding="utf-8"))
    assert [item["candidate_id"] for item in manifest["candidates"]] == ["a", "b", "c"]
    for item in manifest["candidates"]:
        run_dir = Path(item["hatch_run_dir"])
        jobs = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))
        assert any(job["id"] == "base" and job["status"] != "complete" for job in jobs["jobs"])
        assert not (run_dir / "decoded" / "base.png").exists()


def test_preparer_rejects_private_or_chart_content(tmp_path: Path):
    candidates = tmp_path / "unsafe-candidates.json"
    candidate = _safe_candidate("unsafe")
    candidate["birth_date"] = "1990-01-01"
    candidates.write_text(json.dumps({"candidates": [candidate]}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / "prepare_candidate_runs.py"), "--candidates", str(candidates), "--output-dir", str(tmp_path / "runs")],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unsafe" in (result.stderr + result.stdout).lower()


def test_skill_bundles_the_selected_branch_runners_and_their_local_modules():
    required = (
        "candidate_compiler.py",
        "session_contract.py",
        "scripts/prepare_product_session.py",
        "scripts/compute_chart_report.py",
        "scripts/imagegen_preflight.py",
        "scripts/hatch_base_cli.py",
        "scripts/render_character_bible_cli.py",
        "scripts/record_character_bible_qa.py",
        "scripts/record_candidate_boards.py",
        "scripts/record_board_provenance.py",
        "scripts/selected_hatch_run.py",
        "scripts/record_visual_qa.py",
        "scripts/install_selected_pet.py",
        "scripts/session_status.py",
        "scripts/verify_delivery.py",
        "scripts/select_candidate.py",
        "scripts/render_design_branch.py",
        "scripts/prepare_selected_hatch_run.py",
        "scripts/render_character_bible.py",
        "candidate_handoff.py",
        "character_bible.py",
        "companion_ip_contract.py",
        "imagev2.py",
    )
    for relative_path in required:
        assert (SKILL_DIR / relative_path).is_file(), relative_path

    for script in (
        "render_design_branch.py",
        "prepare_selected_hatch_run.py",
        "render_character_bible.py",
        "render_character_bible_cli.py",
        "record_character_bible_qa.py",
        "record_candidate_boards.py",
        "record_board_provenance.py",
        "selected_hatch_run.py",
        "record_visual_qa.py",
        "install_selected_pet.py",
        "session_status.py",
    ):
        result = subprocess.run(
            [sys.executable, str(SKILL_DIR / "scripts" / script), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
