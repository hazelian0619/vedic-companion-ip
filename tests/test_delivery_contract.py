from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_delivery import verify_delivery


def test_delivery_rejects_incomplete_hatch_run(tmp_path: Path):
    result = verify_delivery(tmp_path)
    assert result["ok"] is False
    assert "final/spritesheet.webp" in result["missing"]


def test_delivery_accepts_required_hatch_outputs_and_install_pair(tmp_path: Path):
    (tmp_path / "final").mkdir()
    (tmp_path / "qa" / "previews").mkdir(parents=True)
    (tmp_path / "final" / "spritesheet.webp").write_bytes(b"webp")
    (tmp_path / "final" / "validation.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "qa" / "contact-sheet.png").write_bytes(b"png")
    (tmp_path / "qa" / "review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "qa" / "visual-qa.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    for state in ("idle", "running-right", "running-left", "waving", "jumping", "failed", "waiting", "running", "review"):
        (tmp_path / "qa" / "previews" / f"{state}.gif").write_bytes(b"gif")
    install = tmp_path / "install"
    install.mkdir()
    (install / "pet.json").write_text("{}", encoding="utf-8")
    (install / "spritesheet.webp").write_bytes(b"webp")

    result = verify_delivery(tmp_path, install_dir=install)

    assert result["ok"] is True
    assert result["missing"] == []


def test_delivery_rejects_missing_visual_qa_or_any_state_preview(tmp_path: Path):
    (tmp_path / "final").mkdir()
    (tmp_path / "qa" / "previews").mkdir(parents=True)
    (tmp_path / "final" / "spritesheet.webp").write_bytes(b"webp")
    (tmp_path / "final" / "validation.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "qa" / "contact-sheet.png").write_bytes(b"png")
    (tmp_path / "qa" / "review.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "qa" / "previews" / "idle.gif").write_bytes(b"gif")

    result = verify_delivery(tmp_path)

    assert result["ok"] is False
    assert "qa/visual-qa.json (ok must be true)" in result["missing"]
    assert "qa/previews/running-right.gif" in result["missing"]
