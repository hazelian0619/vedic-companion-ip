#!/usr/bin/env python3
"""Draft 3 companion candidates via an OpenAI-compatible LLM, then gate + record.

Privacy boundary (non-negotiable):
  * The LLM call sends ONLY the de-identified chart facts (asc sign, each
    planet's sign/house/retrograde/dignity, moon nakshatra NAME not pada, dasha
    lord, atmakaraka) plus the authoring framework + the candidate schema. It
    NEVER sends raw birth data, coordinates, dates, chart reports, or rationale.
  * The LLM's candidate output is untrusted text; candidate_validator gates it
    (schema whitelist + privacy_scan + astrology_term_scan, fail-closed) before
    any of it becomes public or reaches the image model.

The drafting-LLM provider is configurable (--llm-base-url / --llm-model /
--api-key-env) so a privacy-conscious user can point it at a local model (e.g.
Ollama). preflight reports which endpoint is configured.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # skill/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from candidate_validator import validate_and_record  # noqa: E402
from session_contract import ProductSession  # noqa: E402

DEFAULT_LLM_URL = "https://tok.fan/v1/chat/completions"
DEFAULT_LLM_MODEL = "gpt-5.4-mini"

# The standardized authoring framework, embedded as the system prompt so the
# script is self-contained. references/candidate-authoring-framework.md is the
# human/agent-readable version of the same thinking.
_SYSTEM_PROMPT = """\
You are a companion-character design director. You read a person's de-identified \
Vedic chart signals and draft exactly THREE genuinely distinct companion-pet \
design directions.

NON-NEGOTIABLE RULES:
- Read chart signals ONLY as design inspiration. Never output astrology terms \
(planet names like Sun/Moon/Saturn, signs like Aries/Cancer, nakshatra, dasha, \
atmakaraka, ascendant, chart, horoscope, jyotish, vedic, house, retrograde, \
rasi, graha). Never output birth data, dates, times, coordinates, or place names.
- The three directions must be genuinely different in BOTH form (shape concept) \
AND silhouette tokens — not three recolorings of one idea.
- Each candidate is compact, endearing, tactile, and has exactly one authored \
signature. No literal animals, no generic blobs, no scenery, no detached effects.
- Output ONLY a JSON object: {"candidates": [c1, c2, c3]}. No prose, no code \
fences, no fields beyond the schema.
- Each candidate object must have EXACTLY these fields (no others): \
candidate_id, ip_name, display_name, description, form_metaphor, \
silhouette_tokens (list of strings), palette_tokens (list), material_tokens \
(list), signature_hook, interaction_signature, board_composition, anti_drift (list).
- candidate_id is a short stable slug like "settling-<short>-1".

FRAMEWORK — how to derive three directions from THIS chart (follow, do not recite):
- ascendant sign          = the companion's outward stance
- atmakaraka (AK) + dignity = the soul's core drive; supported vs strained
- dasha lord              = the current life-rhythm to echo
- moon nakshatra (name)   = temperament texture
- planet dignities        = which energies are available vs strained
- house clusters          = which life-arenas are emphasized
Pick three axes that surface THIS chart's actual tensions (e.g. settling vs \
guiding vs connecting; or rest vs momentum vs repair; or sheltering vs beaconing \
vs bridging) — NOT a fixed taxonomy. Make each direction's form_metaphor AND \
silhouette_tokens genuinely different from the others. Give each a distinct \
signature object and a distinct interaction behavior.

OUTPUT TEMPLATE — return ONLY this JSON with your content substituted in. \
Keep every key exactly as written; add NO keys; drop NO keys; output NO prose \
and NO code fence. Each *_tokens and anti_drift value is a non-empty list of \
short strings:
{"candidates":[
  {"candidate_id":"settling-<short>-1","ip_name":"<coined name>","display_name":"<name>","description":"<one visual-safe sentence>","form_metaphor":"<central poetic object>","silhouette_tokens":["<shape token>","<shape token>"],"palette_tokens":["<color token>","<color token>"],"material_tokens":["<material token>","<material token>"],"signature_hook":"<one stable visual signature>","interaction_signature":"<visual-safe companion behavior>","board_composition":"<visual-safe reading direction>","anti_drift":["<visual constraint>","<visual constraint>"]},
  {"candidate_id":"...-2","ip_name":"...","display_name":"...","description":"...","form_metaphor":"...","silhouette_tokens":["..."],"palette_tokens":["..."],"material_tokens":["..."],"signature_hook":"...","interaction_signature":"...","board_composition":"...","anti_drift":["..."]},
  {"candidate_id":"...-3","ip_name":"...","display_name":"...","description":"...","form_metaphor":"...","silhouette_tokens":["..."],"palette_tokens":["..."],"material_tokens":["..."],"signature_hook":"...","interaction_signature":"...","board_composition":"...","anti_drift":["..."]}
]}
"""


def _load_profile(profile_path: Path) -> tuple[dict, list[str], str]:
    """Return (deidentified_facts, evidence_refs, source_profile_sha256).

    Reads ONLY design_safe_evidence. Raw fields elsewhere in the profile are
    intentionally ignored — they never reach the LLM.
    """
    payload = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    evidence = payload.get("design_safe_evidence") or {}
    facts = evidence.get("deidentified_facts")
    refs = evidence.get("evidence_refs")
    if not isinstance(facts, dict) or not isinstance(refs, list):
        raise ValueError(
            "pet-profile missing design_safe_evidence.deidentified_facts/evidence_refs"
        )
    source_hash = hashlib.sha256(Path(profile_path).read_bytes()).hexdigest()
    return facts, [str(r) for r in refs], source_hash


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)  # bare JSON object in prose
    if m:
        return m.group(0).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)  # bare JSON array in prose
    return m.group(0).strip() if m else text


def _extract_candidates(content: str) -> list | None:
    """Parse the LLM reply and return a candidate list, or None if unparseable.

    Tolerates: code-fenced JSON, a bare {"candidates":[...]} object, or a bare
    [c1,c2,c3] array. Returns None (not raise) so the caller can retry.
    """
    try:
        parsed = json.loads(_strip_code_fence(content))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and isinstance(parsed.get("candidates"), list):
        return parsed["candidates"]
    if isinstance(parsed, list):
        return parsed
    return None


def draft_candidates(
    facts: dict,
    *,
    llm_base_url: str,
    llm_model: str,
    api_key: str,
    timeout: int = 120,
) -> list[dict]:
    """Call the drafting LLM and return exactly 3 candidate dicts (ungated).

    The LLM is non-deterministic and occasionally returns a different JSON shape;
    we parse tolerantly and retry once with a stricter reminder before failing.
    """
    user = (
        "De-identified chart signals (JSON):\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
        + "\n\nDraft exactly three distinct companion candidates per the framework "
        "and schema. Output ONLY the JSON object."
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    for attempt in range(2):
        resp = requests.post(
            llm_base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": llm_model, "messages": messages, "temperature": 0.8},
            timeout=timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text[:300]}")
        content = resp.json()["choices"][0]["message"]["content"]
        candidates = _extract_candidates(content)
        if isinstance(candidates, list) and len(candidates) == 3:
            return candidates
        # retry once with a corrective nudge
        messages.append({"role": "assistant", "content": content})
        messages.append({
            "role": "user",
            "content": "That did not parse as exactly three candidates in the required "
                       "schema. Reply with ONLY a JSON object {\"candidates\":[c1,c2,c3]}, "
                       "each candidate having exactly the schema fields, no prose, no code fence.",
        })
    raise ValueError(
        f"LLM did not return 3 parseable candidates after retry; last content: {content[:200]}"
    )


def author_and_record(
    session_dir: Path,
    *,
    llm_base_url: str = DEFAULT_LLM_URL,
    llm_model: str = DEFAULT_LLM_MODEL,
    api_key_env: str = "IMAGEV2_API_KEY",
) -> Path:
    """Draft 3 candidates via the LLM, preserve a private draft, then gate+record.

    Returns the public safe-candidates.json path. Raises on any privacy/schema
    violation (fail-closed) — in which case no public candidate is written.
    """
    session_dir = Path(session_dir)
    api_key = os.environ.get(api_key_env) or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"API key env var {api_key_env} (or OPENROUTER_API_KEY) not set. "
            "Set it in your OWN process environment; never write it to a file."
        )
    profile_path = session_dir / "private" / "chart" / "pet-profile.json"
    if not profile_path.is_file():
        raise RuntimeError(f"private pet-profile not found: {profile_path}")
    facts, refs, source_hash = _load_profile(profile_path)

    candidates = draft_candidates(
        facts, llm_base_url=llm_base_url, llm_model=llm_model, api_key=api_key
    )

    # Preserve the raw draft privately (provenance), even if validation later fails.
    session = ProductSession.create(session_dir)
    draft_path = session.write_private(
        "candidate-draft.json", {"candidates": candidates, "llm_model": llm_model}
    )

    result = validate_and_record(
        candidates,
        session_dir,
        source_profile_sha256=source_hash,
        evidence_refs=refs,
        llm_model=llm_model,
        draft_path=draft_path,
    )
    return result.candidates_path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--session-dir", required=True, type=Path)
    p.add_argument("--api-key-env", default="IMAGEV2_API_KEY")
    p.add_argument("--llm-base-url", default=DEFAULT_LLM_URL)
    p.add_argument("--llm-model", default=DEFAULT_LLM_MODEL)
    args = p.parse_args()
    try:
        out = author_and_record(
            args.session_dir,
            llm_base_url=args.llm_base_url,
            llm_model=args.llm_model,
            api_key_env=args.api_key_env,
        )
        print(out)
        return 0
    except (OSError, RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
