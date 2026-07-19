#!/usr/bin/env python3
"""Run one official Hatch base job through a user-configured imagegen CLI provider."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


IMAGE_GEN = Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def complete_base_job(run_dir: Path, *, api_key_env: str, image_base_url: Optional[str]) -> Path:
    run = Path(run_dir).resolve()
    if not IMAGE_GEN.is_file():
        raise RuntimeError(f"official imagegen CLI not found: {IMAGE_GEN}")
    key = os.environ.get(api_key_env)
    if not key:
        raise RuntimeError(f"image provider key is not configured in {api_key_env}")
    manifest_path = run / "imagegen-jobs.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    job = next((item for item in manifest.get("jobs", []) if item.get("id") == "base"), None)
    if not job or job.get("status") != "pending":
        raise RuntimeError("official base job is not pending")
    prompt = run / str(job.get("prompt_file", ""))
    output = run / str(job.get("output_path", ""))
    if not prompt.is_file() or not output.name:
        raise RuntimeError("official base job is missing its prompt or output path")
    environment = dict(os.environ)
    environment["OPENAI_API_KEY"] = key
    if image_base_url:
        environment["OPENAI_BASE_URL"] = image_base_url.rstrip("/")
    command = [
        sys.executable,
        str(IMAGE_GEN),
        "generate",
        "--prompt-file", str(prompt),
        "--use-case", "stylized-concept",
        "--quality", "high",
        "--size", "1024x1024",
        "--out", str(output),
        "--no-augment",
    ]
    subprocess.run(command, env=environment, check=True)
    if not output.is_file():
        raise RuntimeError("official imagegen CLI finished without producing the Hatch base")
    canonical = run / "references" / "canonical-base.png"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, canonical)
    job.update({"status": "complete", "source_path": str(output), "completed_at": _timestamp()})
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--image-base-url")
    args = parser.parse_args()
    try:
        print(complete_base_job(args.run_dir, api_key_env=args.api_key_env, image_base_url=args.image_base_url))
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
