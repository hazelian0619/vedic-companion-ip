#!/usr/bin/env python3
"""Real onboarding preflight: detect + auto-install missing deps, verify the image API.

This is NOT a mock. It really checks for VEDIC_PY / hatch-pet / imagegen, really
verifies the image API with a live /v1/models call, and (with --auto-install, the
default) really installs missing pieces into clearly-scoped locations. --check is
read-only (for CI/tests).

Credentials are read ONLY from process env vars and are NEVER printed, written to
files, or sent anywhere except the bearer header of the verification call itself.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # skill/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

DEFAULT_API_BASE = "https://tok.fan/v1"
DEFAULT_IMAGEN_MODEL = "gpt-image-2"

# status codes
OK = "ok"
INSTALLED = "installed"
MISSING = "missing"      # blocker
WARN = "warn"           # non-blocker (reachable-but-odd, or transient)


def _vedic_default() -> Path:
    return Path.home() / ".claude" / "skills" / "vedic-calculator" / "venv" / "bin" / "python"


def _skill_local_venv() -> Path:
    return Path.home() / ".claude" / "skills" / "vedic-companion-ip" / "vedic-venv" / "bin" / "python"


def _hatch_pet_dir() -> Path:
    return Path.home() / ".codex" / "skills" / "hatch-pet"


def _imagegen_dir() -> Path:
    return Path.home() / ".codex" / "skills" / ".system" / "imagegen"


def ensure_vedic_py(*, auto_install: bool) -> tuple[str, str, str]:
    skill_local = _skill_local_venv()
    candidate = Path(os.environ.get("VEDIC_PY", str(_vedic_default())))
    if candidate.is_file():
        return ("VEDIC_PY", OK, str(candidate))
    if not auto_install:
        return ("VEDIC_PY", MISSING, f"not found at {candidate}; set VEDIC_PY or run with --auto-install")
    # auto-install into a clearly-scoped skill-local venv (never the system python)
    venv_root = skill_local.parent
    try:
        if not skill_local.is_file():
            subprocess.run([sys.executable, "-m", "venv", str(venv_root)], check=True, capture_output=True)
        subprocess.run(
            [str(skill_local), "-m", "pip", "install", "--quiet", "pysweph", "pyjhora"],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        return ("VEDIC_PY", MISSING, f"auto-install failed: {(e.stderr or b'').decode()[:200]}")
    return ("VEDIC_PY", INSTALLED, f"created venv at {venv_root}; set VEDIC_PY={skill_local} for reuse")


def ensure_hatch_pet(*, auto_install: bool) -> tuple[str, str, str]:
    hatch_dir = _hatch_pet_dir()
    if hatch_dir.exists():
        return ("hatch-pet", OK, str(hatch_dir))
    repo = os.environ.get("HATCH_PET_REPO")
    if auto_install and repo:
        try:
            hatch_dir.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", repo, str(hatch_dir)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return ("hatch-pet", MISSING, f"clone failed: {(e.stderr or b'').decode()[:200]}")
        return ("hatch-pet", INSTALLED, str(hatch_dir))
    hint = "install the official hatch-pet skill, or set HATCH_PET_REPO=<git-url> and --auto-install"
    return ("hatch-pet", MISSING, f"not found at {hatch_dir}; {hint}")


def ensure_imagegen() -> tuple[str, str, str]:
    imagegen_dir = _imagegen_dir()
    if imagegen_dir.exists():
        return ("imagegen", OK, str(imagegen_dir))
    return ("imagegen", MISSING, f"not found at {imagegen_dir}; install the .system imagegen skill")


def check_api() -> tuple[str, str, str]:
    """Verify the image API for real with /v1/models. Never print the key."""
    key = os.environ.get("IMAGEV2_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    base = os.environ.get("IMAGEV2_ENDPOINT", DEFAULT_API_BASE)
    model = os.environ.get("IMAGEN_MODEL", DEFAULT_IMAGEN_MODEL)
    if not key:
        return ("image-api", MISSING,
                "set IMAGEV2_API_KEY (or OPENROUTER_API_KEY) in your OWN process env; "
                "never write it to a file/repo/prompt")
    try:
        r = requests.get(base.rstrip("/") + "/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=15)
    except Exception as e:  # noqa: BLE001
        return ("image-api", WARN, f"{base} unreachable: {e}")
    if r.status_code != 200:
        return ("image-api", WARN, f"{base} HTTP {r.status_code}; check key/endpoint")
    ids = [m.get("id") for m in r.json().get("data", [])] if r.json().get("data") else []
    has_image = any("image" in str(i).lower() for i in ids)
    return ("image-api", OK if has_image else WARN,
            f"{base} reachable; {len(ids)} models; image-model={'yes' if has_image else 'NO'}; "
            f"IMAGEN_MODEL={model}")


def run_preflight(*, auto_install: bool) -> list[tuple[str, str, str]]:
    return [
        ensure_vedic_py(auto_install=auto_install),
        ensure_hatch_pet(auto_install=auto_install),
        ensure_imagegen(),
        check_api(),
    ]


def _print(results: list[tuple[str, str, str]]) -> bool:
    print(f"{'check':<12} {'status':<10} detail")
    print("-" * 60)
    blocked = False
    for name, status, detail in results:
        print(f"{name:<12} {status:<10} {detail}")
        if status == MISSING:
            blocked = True
    return blocked


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--auto-install", dest="auto_install", action="store_true", default=True)
    p.add_argument("--no-auto-install", dest="auto_install", action="store_false")
    p.add_argument("--check", action="store_true", help="read-only; never install (for CI/tests)")
    args = p.parse_args()
    auto = args.auto_install and not args.check
    blocked = _print(run_preflight(auto_install=auto))
    if blocked:
        print("\nBLOCKED: a required dependency is missing. Resolve above before continuing.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
