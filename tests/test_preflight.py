"""Tests for preflight onboarding. Network + subprocess are mocked (CI-safe, no spend)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skill"))
from scripts import preflight  # noqa: E402


class _Completed:
    """Minimal subprocess.CompletedProcess stand-in."""
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
        self.text = ""

    def json(self):
        return self._p


# ---------------- VEDIC_PY ---------------- #

def test_missing_vedic_py_auto_installs_into_scoped_venv(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("VEDIC_PY", raising=False)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")  # stable for the venv cmd
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        return _Completed(0)
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    name, status, detail = preflight.ensure_vedic_py(auto_install=True)
    assert status == preflight.INSTALLED
    assert any("venv" in c for c in calls), "should create a venv"
    assert any("pip" in c and "pysweph" in c for c in calls), "should install pysweph + pyjhora"
    # installed into a skill-local path, not the system python
    assert str(tmp_path) in detail or "vedic-companion-ip" in detail


def test_check_mode_does_not_install(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("VEDIC_PY", raising=False)
    monkeypatch.setattr(preflight.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not install in --check")))
    name, status, detail = preflight.ensure_vedic_py(auto_install=False)
    assert status == preflight.MISSING
    assert "auto-install" in detail or "VEDIC_PY" in detail


def test_found_vedic_py_is_ok(tmp_path, monkeypatch):
    fake_py = tmp_path / "vedic-python"
    fake_py.write_text("", encoding="utf-8")
    monkeypatch.setenv("VEDIC_PY", str(fake_py))
    name, status, detail = preflight.ensure_vedic_py(auto_install=False)
    assert status == preflight.OK
    assert str(fake_py) in detail


# ---------------- hatch-pet ---------------- #

def test_missing_hatch_pet_reports_instructions_without_repo(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("HATCH_PET_REPO", raising=False)
    name, status, detail = preflight.ensure_hatch_pet(auto_install=True)
    assert status == preflight.MISSING
    assert "HATCH_PET_REPO" in detail or "hatch-pet" in detail


def test_missing_hatch_pet_auto_clones_when_repo_set(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("HATCH_PET_REPO", "https://example/hatch-pet.git")
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        # simulate clone by creating the dir
        Path(cmd[-1]).mkdir(parents=True, exist_ok=True)
        return _Completed(0)
    monkeypatch.setattr(preflight.subprocess, "run", fake_run)
    name, status, detail = preflight.ensure_hatch_pet(auto_install=True)
    assert status == preflight.INSTALLED
    assert calls and calls[0][0] == "git" and calls[0][1] == "clone"


# ---------------- image API ---------------- #

def test_api_ok_when_reachable_with_image_model(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGEV2_API_KEY", "sk-secret-key-must-not-print")
    monkeypatch.setenv("IMAGEV2_ENDPOINT", "https://tok.fan/v1")
    monkeypatch.setattr(
        preflight.requests, "get",
        lambda url, headers=None, timeout=None: _FakeResp(200, {"data": [{"id": "gpt-image-2"}, {"id": "gpt-5.4"}]}),
    )
    name, status, detail = preflight.check_api()
    assert status == preflight.OK
    assert "sk-secret-key-must-not-print" not in detail  # key never in output
    assert "image-model=yes" in detail


def test_api_missing_when_no_key(monkeypatch):
    monkeypatch.delenv("IMAGEV2_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    name, status, detail = preflight.check_api()
    assert status == preflight.MISSING
    assert "IMAGEV2_API_KEY" in detail
    assert "file" in detail.lower() or "env" in detail.lower()


def test_api_warns_when_unreachable(monkeypatch):
    monkeypatch.setenv("IMAGEV2_API_KEY", "sk-x")
    def boom(*a, **k):
        raise ConnectionError("DNS fail")
    monkeypatch.setattr(preflight.requests, "get", boom)
    name, status, detail = preflight.check_api()
    assert status == preflight.WARN  # non-blocker (could be transient)


# ---------------- exit code ---------------- #

def test_run_preflight_blocks_on_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("VEDIC_PY", raising=False)
    monkeypatch.delenv("IMAGEV2_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("HATCH_PET_REPO", raising=False)
    results = preflight.run_preflight(auto_install=False)
    assert any(r[1] == preflight.MISSING for r in results)
    blocked = preflight._print(results)
    assert blocked is True
    out = capsys.readouterr()
    assert "sk-" not in out.out and "sk-" not in out.err  # no key leaked
