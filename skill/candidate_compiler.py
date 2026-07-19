"""Compile local chart evidence into three image-safe companion directions."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from companion_ip_contract import astrology_term_scan, privacy_scan
from session_contract import ProductSession


_ELEMENTS = {
    "Aries": "spark", "Leo": "spark", "Sagittarius": "spark",
    "Taurus": "anchor", "Virgo": "anchor", "Capricorn": "anchor",
    "Gemini": "bridge", "Libra": "bridge", "Aquarius": "bridge",
    "Cancer": "shelter", "Scorpio": "shelter", "Pisces": "shelter",
}
_HOUSES = {
    1: "spark", 5: "spark", 9: "spark",
    2: "anchor", 6: "anchor", 10: "anchor",
    3: "bridge", 7: "bridge", 11: "bridge",
    4: "shelter", 8: "shelter", 12: "shelter",
}
_DIRECTIONS = ("shelter", "beacon", "bridge")
_DIRECTION_SIGNAL = {"shelter": "shelter", "beacon": "spark", "bridge": "bridge"}
_NAME_PREFIX = ("Ari", "Nelo", "Sumi", "Tavi", "Mori", "Luma", "Kiro", "Vela")


@dataclass(frozen=True)
class CompiledCandidates:
    candidates_path: Path
    private_ledger_path: Path
    session: ProductSession


def _load_profile(path: Path) -> tuple[dict[str, Any], list[str]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    evidence = payload.get("design_safe_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("pet profile requires design_safe_evidence")
    facts = evidence.get("deidentified_facts")
    refs = evidence.get("evidence_refs")
    if not isinstance(facts, dict) or not isinstance(facts.get("planets"), dict) or not isinstance(refs, list):
        raise ValueError("pet profile is incomplete")
    return facts, [str(item) for item in refs]


def _signal_scores(facts: dict[str, Any]) -> dict[str, int]:
    scores = {"spark": 0, "anchor": 0, "bridge": 0, "shelter": 0}
    asc = _ELEMENTS.get(str(facts.get("asc_sign")))
    if asc:
        scores[asc] += 2
    for planet in facts["planets"].values():
        if not isinstance(planet, dict):
            continue
        element = _ELEMENTS.get(str(planet.get("sign")))
        house = _HOUSES.get(planet.get("house"))
        if element:
            scores[element] += 2
        if house:
            scores[house] += 1
    return scores


def _evidence_for(direction: str, facts: dict[str, Any], refs: list[str]) -> list[str]:
    matching: list[str] = []
    for ref in refs:
        parts = ref.split(":")
        if len(parts) >= 2 and _ELEMENTS.get(parts[-1]) == direction:
            matching.append(ref)
        if "house" in parts:
            try:
                house = int(parts[-1])
            except ValueError:
                continue
            if _HOUSES.get(house) == direction:
                matching.append(ref)
    if len(matching) < 2:
        matching.extend(refs)
    return list(dict.fromkeys(matching))[:2]


def _candidate(direction: str, rank: int, digest: str) -> dict[str, Any]:
    name = _NAME_PREFIX[int(digest[rank * 2:rank * 2 + 2], 16) % len(_NAME_PREFIX)]
    definitions = {
        "shelter": {
            "description": "A compact companion that protects a quiet center while staying emotionally present.",
            "form_metaphor": "A small folded shelter holding one protected inner signal.",
            "silhouette_tokens": ["enclosing upper shell", "wide planted lower mass", "calm face opening"],
            "palette_tokens": ["dominant resting field", "quiet light-value face zone", "one contained living accent"],
            "material_tokens": ["layered tactile outer shell", "matte inner face surface", "small structural joins"],
            "signature_hook": "One protected core integrated at the center of the body.",
        },
        "beacon": {
            "description": "A compact companion that turns focused attention into a calm, guiding presence.",
            "form_metaphor": "A small upright keeper carrying one focused guiding signal.",
            "silhouette_tokens": ["soft vertical crown", "compact balanced body", "clear central spine"],
            "palette_tokens": ["supporting outer field", "clear face-value break", "one focused active accent"],
            "material_tokens": ["soft layered outer surface", "precise central fitting", "translucent focal detail"],
            "signature_hook": "One focused signal held on the central axis.",
        },
        "bridge": {
            "description": "A compact companion that makes connection feel steady, mutual, and easy to approach.",
            "form_metaphor": "A small linked form that holds two calm sides around one shared center.",
            "silhouette_tokens": ["rounded paired side forms", "stable shared base", "open central face zone"],
            "palette_tokens": ["grounding outer field", "welcoming light face zone", "one connecting accent"],
            "material_tokens": ["tactile paired layers", "matte face surface", "small linking hardware"],
            "signature_hook": "One visible connection detail joining the two sides at the center.",
        },
    }[direction]
    return {
        "candidate_id": f"{direction}-{digest[:6]}-{rank + 1}",
        "ip_name": f"{name} {direction.title()}",
        "display_name": f"{name} / {direction.title()}",
        **definitions,
        "anti_drift": [
            "no literal animal",
            "no generic blob",
            "no scenery",
            "no detached effects",
            "keep the companion compact and emotionally present",
        ],
    }


def compile_candidates(profile_path: Path, session_root: Path) -> CompiledCandidates:
    facts, refs = _load_profile(Path(profile_path))
    source_hash = hashlib.sha256(Path(profile_path).read_bytes()).hexdigest()
    scores = _signal_scores(facts)
    ranked = sorted(
        _DIRECTIONS,
        key=lambda item: (-scores[_DIRECTION_SIGNAL[item]], _DIRECTIONS.index(item)),
    )
    digest = hashlib.sha256(json.dumps(facts, sort_keys=True).encode("utf-8")).hexdigest()
    candidates = [_candidate(direction, rank, digest) for rank, direction in enumerate(ranked)]
    for candidate in candidates:
        serialized = json.dumps(candidate, ensure_ascii=False)
        if astrology_term_scan(serialized) or not privacy_scan(serialized)[0]:
            raise ValueError("candidate compiler produced unsafe visual content")
    session = ProductSession.create(Path(session_root))
    candidates_path = session.write_public("safe-candidates.json", {"candidates": candidates})
    ledger = {
        "compiler_version": 1,
        "source_profile_sha256": source_hash,
        "candidate_evidence": [
            {
                "candidate_id": candidate["candidate_id"],
                "direction": direction,
                "score": scores[_DIRECTION_SIGNAL[direction]],
                "evidence_refs": _evidence_for(_DIRECTION_SIGNAL[direction], facts, refs),
            }
            for candidate, direction in zip(candidates, ranked)
        ],
    }
    ledger_path = session.write_private("candidate-evidence.json", ledger)
    session.transition("candidates_ready", artifact_paths=[candidates_path], decision="compiled three visual-safe directions")
    return CompiledCandidates(candidates_path=candidates_path, private_ledger_path=ledger_path, session=session)
