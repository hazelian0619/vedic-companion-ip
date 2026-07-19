"""Resumable, privacy-aware session records for companion production."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


_STATES = (
    "intake_ready",
    "chart_ready",
    "candidates_ready",
    "identity_boards_ready",
    "identity_selected",
    "selected_hatch_ready",
    "candidate_runs_ready",
    "candidate_bases_ready",
    "candidate_boards_ready",
    "candidate_selected",
    "base_accepted",
    "animation_ready",
    "package_validated",
    "installed",
)

_ALLOWED_TRANSITIONS = {
    "intake_ready": frozenset({"chart_ready"}),
    "chart_ready": frozenset({"candidates_ready"}),
    "candidates_ready": frozenset({"candidate_runs_ready", "identity_boards_ready"}),
    "identity_boards_ready": frozenset({"identity_selected"}),
    "identity_selected": frozenset({"selected_hatch_ready"}),
    "selected_hatch_ready": frozenset({"base_accepted"}),
    "candidate_runs_ready": frozenset({"candidate_bases_ready"}),
    "candidate_bases_ready": frozenset({"candidate_boards_ready"}),
    "candidate_boards_ready": frozenset({"candidate_selected"}),
    "candidate_selected": frozenset({"base_accepted", "animation_ready"}),
    "base_accepted": frozenset({"animation_ready"}),
    "animation_ready": frozenset({"package_validated"}),
    "package_validated": frozenset({"installed"}),
    "installed": frozenset(),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class ProductSession:
    root: Path
    session_id: str

    @classmethod
    def create(cls, root: Path) -> "ProductSession":
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        private_dir = root / "private"
        private_dir.mkdir(exist_ok=True)
        os.chmod(private_dir, 0o700)
        manifest_path = root / "session.json"
        if manifest_path.exists():
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            return cls(root=root, session_id=str(payload["session_id"]))
        session = cls(root=root, session_id=f"session-{secrets.token_hex(8)}")
        session.write_public(
            "session.json",
            {"session_id": session.session_id, "state": "intake_ready", "created_at": _utc_now(), "events": []},
        )
        return session

    def _resolve(self, relative_path: str, *, private: bool) -> Path:
        base = self.root / "private" if private else self.root
        path = (base / relative_path).resolve()
        if base not in path.parents and path != base:
            raise ValueError("session artifact must remain inside its session directory")
        return path

    def _write(self, path: Path, payload: dict[str, Any], mode: int) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700 if "private" in path.parts else 0o755)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        os.chmod(path, mode)
        return path

    def write_private(self, relative_path: str, payload: dict[str, Any]) -> Path:
        return self._write(self._resolve(relative_path, private=True), payload, 0o600)

    def write_public(self, relative_path: str, payload: dict[str, Any]) -> Path:
        return self._write(self._resolve(relative_path, private=False), payload, 0o644)

    def _artifact_hashes(self, artifact_paths: Iterable[Path]) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for artifact in artifact_paths:
            path = Path(artifact).resolve()
            if not path.is_file() or self.root not in path.parents:
                raise ValueError("session transition artifact is missing or outside the session")
            if self.root / "private" in path.parents:
                raise ValueError("private artifacts cannot appear in a public session transition")
            hashes[str(path.relative_to(self.root))] = _sha256(path)
        return hashes

    def transition(self, state: str, *, artifact_paths: Iterable[Path], decision: str) -> None:
        if state not in _STATES:
            raise ValueError(f"unknown session state: {state}")
        manifest_path = self.root / "session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        current = str(manifest["state"])
        if state not in _ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"session transition from {current} to {state} is not allowed")
        hashes = self._artifact_hashes(artifact_paths)
        manifest["state"] = state
        manifest["events"].append(
            {"at": _utc_now(), "state": state, "decision": decision, "artifact_hashes": hashes}
        )
        self.write_public("session.json", manifest)

    def record_event(self, kind: str, *, artifact_paths: Iterable[Path], decision: str) -> None:
        normalized_kind = "_".join(kind.split())
        if not normalized_kind or not normalized_kind.replace("_", "").isalnum():
            raise ValueError("public event kind must contain only letters, digits, and underscores")
        manifest_path = self.root / "session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["events"].append(
            {
                "at": _utc_now(),
                "state": manifest["state"],
                "kind": normalized_kind,
                "decision": decision,
                "artifact_hashes": self._artifact_hashes(artifact_paths),
            }
        )
        self.write_public("session.json", manifest)
