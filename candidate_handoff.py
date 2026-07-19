"""Safe boundaries between candidate synthesis and visual production."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from companion_ip_contract import astrology_term_scan, privacy_scan


_PRIVATE_KEYS = frozenset(
    {
        "private_rationale",
        "design_rationale",
        "chart_report",
        "birth_date",
        "birth_time",
        "birth_place",
        "timezone",
        "latitude",
        "longitude",
    }
)


def _safe_text(value: Any) -> str:
    return " ".join(str(value).split())


def _validate_candidate(candidate: dict[str, Any]) -> None:
    if _PRIVATE_KEYS.intersection(candidate):
        raise ValueError("unsafe candidate content")

    serialized = json.dumps(candidate, ensure_ascii=False)
    private_findings = privacy_scan(serialized)[1]
    astrology_findings = astrology_term_scan(serialized)
    if private_findings or astrology_findings:
        raise ValueError("unsafe candidate content")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("candidate_id must contain letters or digits")
    return slug


def build_hatch_handoff(candidate: dict[str, Any], *, candidate_id: str) -> dict[str, str]:
    """Create the minimal design-safe input accepted by official hatch-pet."""
    _validate_candidate(candidate)
    pet_name = _safe_text(candidate.get("ip_name"))
    if not pet_name:
        raise ValueError("candidate must include ip_name")

    palette = ", ".join(_safe_text(item) for item in candidate.get("palette_tokens", []))
    materials = ", ".join(_safe_text(item) for item in candidate.get("material_tokens", []))
    silhouette = ", ".join(_safe_text(item) for item in candidate.get("silhouette_tokens", []))
    avoid = "; ".join(_safe_text(item) for item in candidate.get("anti_drift", []))

    return {
        "pet_name": pet_name,
        "pet_id": _slug(candidate_id),
        "display_name": _safe_text(candidate.get("display_name") or pet_name),
        "description": _safe_text(candidate.get("subject_archetype") or candidate.get("form_metaphor")),
        "pet_notes": (
            f"{_safe_text(candidate.get('form_metaphor'))}. "
            f"Silhouette: {silhouette}. "
            f"Signature: {_safe_text(candidate.get('signature_hook'))}. "
            f"Interaction: {_safe_text(candidate.get('interaction_signature'))}. "
            f"Avoid: {avoid}."
        ),
        "style_notes": f"Palette: {palette}. Materials: {materials}. Keep the character compact and readable at pet size.",
    }


def build_board_input(
    candidate: dict[str, Any], *, official_base_path: str | Path, board_reference_path: str | Path = "", board_system: str = "professional-editorial-v3"
) -> dict[str, Any]:
    """Create imagev2 input that is grounded in an official hatch-pet base."""
    _validate_candidate(candidate)
    if not str(official_base_path).strip():
        raise ValueError("an official hatch-pet base is required")
    base_path = Path(official_base_path)
    board_path = Path(board_reference_path) if str(board_reference_path).strip() else None

    return {
        "official_base_path": str(base_path),
        "board_reference_path": str(board_path) if board_path else "",
        "board_system": board_system,
        "ip_name": _safe_text(candidate.get("ip_name")),
        "display_name": _safe_text(candidate.get("display_name")),
        "form_metaphor": _safe_text(candidate.get("form_metaphor")),
        "silhouette_tokens": [_safe_text(item) for item in candidate.get("silhouette_tokens", [])],
        "palette_tokens": [_safe_text(item) for item in candidate.get("palette_tokens", [])],
        "material_tokens": [_safe_text(item) for item in candidate.get("material_tokens", [])],
        "signature_hook": _safe_text(candidate.get("signature_hook")),
        "interaction_signature": _safe_text(candidate.get("interaction_signature")),
        "board_composition": _safe_text(candidate.get("board_composition")),
        "anti_drift": [_safe_text(item) for item in candidate.get("anti_drift", [])],
    }
