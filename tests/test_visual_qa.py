from __future__ import annotations

import json
from pathlib import Path

from scripts.record_visual_qa import record_visual_qa


def test_record_visual_qa_requires_deterministic_artifacts_and_all_state_previews(tmp_path: Path):
    (tmp_path / "final").mkdir()
    (tmp_path / "qa" / "previews").mkdir(parents=True)
    (tmp_path / "final" / "validation.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "qa" / "contact-sheet.png").write_bytes(b"png")
    (tmp_path / "qa" / "review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    for state in ("idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review"):
        (tmp_path / "qa" / "previews" / f"{state}.gif").write_bytes(b"gif")

    artifact = record_visual_qa(tmp_path, reviewer="visual-agent", note="identity and motion pass")

    assert json.loads(artifact.read_text(encoding="utf-8")) == {
        "ok": True,
        "reviewer": "visual-agent",
        "note": "identity and motion pass",
    }
