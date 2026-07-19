#!/usr/bin/env python3
"""Report whether the official imagegen CLI is configured without exposing secrets."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Optional


def inspect_imagegen(*, cli_path: Optional[Path] = None) -> dict[str, Any]:
    cli = Path(cli_path or Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py")
    key_configured = bool(os.environ.get("OPENAI_API_KEY"))
    cli_available = cli.is_file()
    return {
        "status": "ready_to_attempt" if cli_available and key_configured else "blocked",
        "model": "gpt-image-2",
        "cli_path": str(cli),
        "cli_available": cli_available,
        "openai_api_key_configured": key_configured,
        "note": "Authentication validity is verified only by a real generation request.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = inspect_imagegen()
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "ready_to_attempt" else 2


if __name__ == "__main__":
    raise SystemExit(main())
