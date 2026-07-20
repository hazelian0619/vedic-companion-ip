from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skill"))
MODULE_PATH = ROOT / "skill" / "scripts" / "render_design_branch.py"
SPEC = importlib.util.spec_from_file_location("render_design_branch", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_identity_seed_uses_official_request_without_chroma_production_rules(tmp_path: Path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "base-pet.md").write_text(
        "Keep the character compact. Place it on a pure magenta #FF00FF chroma-key background.",
        encoding="utf-8",
    )
    (tmp_path / "pet_request.json").write_text(
        json.dumps(
            {
                "description": "A compact keeper.",
                "pet_notes": "One protected central light.",
                "style_notes": "Use the selected branch reference.",
                "chroma_key": {"hex": "#FF00FF"},
            }
        ),
        encoding="utf-8",
    )

    seed = MODULE.identity_seed(tmp_path)

    assert "compact keeper" in seed
    assert "protected central light" in seed
    assert "magenta" not in seed.lower()
    assert "#ff00ff" not in seed.lower()


def test_branch_identity_is_generated_from_the_branch_board_not_in_parallel(tmp_path: Path):
    calls = []

    def fake_generate(prompt, out, *, refs):
        calls.append((prompt, Path(out), [Path(path) for path in refs]))
        Path(out).write_bytes(b"image")
        return Path(out)

    request = {
        "board_prompt": "board",
        "identity_reference_prompt": "identity",
        "reference_paths": ["/tmp/board-system.png"],
    }

    MODULE.render_branch_outputs(request, tmp_path, generate_fn=fake_generate)

    assert calls[0][2] == [Path("/tmp/board-system.png")]
    assert calls[1][2] == [tmp_path / "branch-board.png"]
