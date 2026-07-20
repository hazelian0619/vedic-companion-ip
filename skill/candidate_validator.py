"""Validate and record LLM-authored companion candidates behind a hard privacy gate.

This module replaces the legacy deterministic ``candidate_compiler`` (a lookup
table of 3 fixed archetypes x 9 templates x 81 surface combos). Authoring is now
done by an LLM (``scripts/author_candidates.py``); this module is the
**gate**: it takes 3 drafted candidates, enforces the privacy contract and the
schema whitelist fail-closed, requires 3 genuinely distinct directions, records
a public ``safe-candidates.json`` + a private evidence ledger, and advances the
session to ``candidates_ready``.

Privacy boundary (non-negotiable):
  * Candidates are LLM-authored, so their TEXT is untrusted until gated.
  * Every candidate is ``privacy_scan`` + ``astrology_term_scan``'d (English
    whole-word + Chinese) and schema-whitelist-checked. Any failure raises and
    nothing public is written; the session state does not advance.
  * The public ``safe-candidates.json`` carries ONLY the 12 schema fields per
    candidate. Evidence refs, source-profile hash, and the LLM model stay in the
    private ledger.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from companion_ip_contract import (
    astrology_term_scan,
    privacy_scan,
    validate_candidate_schema,
)
from session_contract import ProductSession

#: Fields that MUST be present on every candidate (the contract-required subset
#: of CANDIDATE_SCHEMA_FIELDS). ``interaction_signature`` and ``board_composition``
#: are required for production candidates (legacy validated manifests may omit
#: them; author_candidates always emits them).
_REQUIRED_PRESENT = (
    "candidate_id",
    "ip_name",
    "display_name",
    "form_metaphor",
    "silhouette_tokens",
    "palette_tokens",
    "material_tokens",
    "signature_hook",
    "interaction_signature",
    "board_composition",
    "anti_drift",
)

#: Soft description; not privacy-sensitive, but required by the contract.
_OPTIONAL_PRESENT = ("description",)


@dataclass(frozen=True)
class RecordedCandidates:
    """Result of a successful validation+record. Public path + private ledger."""
    candidates_path: Path       # public safe-candidates.json
    private_ledger_path: Path   # private/candidate-evidence.json
    session: ProductSession


def _slug(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not s:
        raise ValueError("candidate_id must contain letters or digits")
    return s


def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError("token list must be a list of strings")
    return [str(x) for x in value]


def _check_one(candidate: Any) -> None:
    """Gate a single candidate. Raises ValueError on any violation (fail-closed)."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a JSON object")

    unknown = validate_candidate_schema(candidate)
    if unknown:
        raise ValueError(f"candidate has unknown fields: {', '.join(unknown)}")

    for field_name in _REQUIRED_PRESENT:
        if field_name not in candidate:
            raise ValueError(f"candidate missing required field: {field_name}")

    _slug(str(candidate["candidate_id"]))
    # The 3 visual token lists must be non-empty lists of strings (a candidate
    # with empty silhouette/palette/material is not a real direction). anti_drift
    # may be empty (constraints are optional).
    for tok_field in ("silhouette_tokens", "palette_tokens", "material_tokens"):
        toks = _as_text_list(candidate[tok_field])
        if not toks:
            raise ValueError(f"candidate {tok_field} must not be empty")
    _as_text_list(candidate["anti_drift"])
    for str_field in ("ip_name", "display_name", "form_metaphor", "signature_hook",
                       "interaction_signature", "board_composition"):
        if not str(candidate[str_field]).strip():
            raise ValueError(f"candidate field empty: {str_field}")

    blob = json.dumps(candidate, ensure_ascii=False)
    priv_clean, priv_findings = privacy_scan(blob)
    if not priv_clean:
        raise ValueError(f"candidate failed privacy_scan: {priv_findings}")
    astro = astrology_term_scan(blob)
    if astro:
        raise ValueError(f"candidate contains astrology term(s): {astro}")


def _pair_distinct(a: dict, b: dict) -> bool:
    """Two candidates are distinct iff form_metaphor AND silhouette_tokens both differ.

    A pair that shares form_metaphor and silhouette_tokens is either identical
    or merely recolored (palette-only difference) — not a distinct direction.
    """
    form_differs = str(a["form_metaphor"]) != str(b["form_metaphor"])
    sil_differs = _as_text_list(a["silhouette_tokens"]) != _as_text_list(b["silhouette_tokens"])
    return form_differs and sil_differs


def _check_distinct(candidates: list[dict]) -> None:
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            if not _pair_distinct(candidates[i], candidates[j]):
                raise ValueError(
                    "candidates are not distinct: a pair shares form_metaphor and "
                    "silhouette_tokens (identical or merely recolored)"
                )


def validate_and_record(
    candidates: list[dict],
    session_root: Path,
    *,
    source_profile_sha256: str,
    evidence_refs: list[str],
    llm_model: str = "",
    draft_path: Path | None = None,
) -> RecordedCandidates:
    """Gate 3 LLM-authored candidates and record them. Fail-closed on any violation.

    Parameters
    ----------
    candidates:
        Exactly 3 candidate dicts authored by the LLM drafter.
    session_root:
        The product session directory (must already be in ``chart_ready``).
    source_profile_sha256:
        sha256 of the private pet-profile the candidates were derived from
        (provenance; the profile itself never leaves the private boundary).
    evidence_refs:
        De-identified refs (e.g. ``asc_sign:Aries``) carried into the private
        ledger only. Never written to the public candidate file.
    llm_model:
        The drafting model identifier, recorded privately for auditability.
    draft_path:
        Optional path to the private raw LLM draft, recorded as provenance.
    """
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise ValueError("exactly three candidates required")
    if not isinstance(source_profile_sha256, str) or not source_profile_sha256:
        raise ValueError("source_profile_sha256 must be a non-empty string")
    if not isinstance(evidence_refs, list) or not all(isinstance(r, str) for r in evidence_refs):
        raise ValueError("evidence_refs must be a list of strings")

    # _check_one raises ValueError for non-dict candidates (and missing fields,
    # schema/scan violations) BEFORE we ever subscript candidate_id, so a
    # non-dict candidate fails closed with a contract error, not a TypeError.
    for c in candidates:
        _check_one(c)
    _check_distinct(candidates)
    ids = [str(c["candidate_id"]) for c in candidates]
    if len(set(ids)) != 3:
        raise ValueError("candidate_ids must be unique")

    session = ProductSession.create(Path(session_root))
    candidates_path = session.write_public(
        "safe-candidates.json", {"candidates": candidates}
    )
    ledger = {
        "validator_version": 3,
        "authored_by": "llm",
        "llm_model": llm_model,
        "source_profile_sha256": source_profile_sha256,
        "draft_path": str(draft_path) if draft_path else "",
        "candidate_hashes": [
            {
                "candidate_id": str(c["candidate_id"]),
                "sha256": hashlib.sha256(
                    json.dumps(c, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
            }
            for c in candidates
        ],
        "evidence_refs": list(evidence_refs),
    }
    ledger_path = session.write_private("candidate-evidence.json", ledger)

    session.transition(
        "candidates_ready",
        artifact_paths=[candidates_path],
        decision="LLM-authored 3 visual-safe directions, gated",
    )
    return RecordedCandidates(
        candidates_path=candidates_path,
        private_ledger_path=ledger_path,
        session=session,
    )
