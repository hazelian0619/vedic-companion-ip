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
_DIRECTION_OFFSET = {"shelter": 0, "beacon": 3, "bridge": 6}
_PALETTE_RELATIONSHIPS = (
    ("moss outer structure", "celadon face plane", "vermilion signal detail"),
    ("mulberry outer structure", "blush face plane", "cool cyan signal detail"),
    ("petrol outer structure", "mint face plane", "cinnabar signal detail"),
    ("cobalt outer structure", "lemon face plane", "coral signal detail"),
    ("berry outer structure", "cloud face plane", "lime signal detail"),
    ("saffron outer structure", "dusty rose face plane", "indigo signal detail"),
    ("slate outer structure", "apricot face plane", "emerald signal detail"),
    ("pine outer structure", "pearl face plane", "scarlet signal detail"),
    ("charcoal outer structure", "seafoam face plane", "magenta signal detail"),
)
_MATERIAL_RELATIONSHIPS = (
    ("matte ceramic outer shell", "woven fabric face surround", "brushed aluminum join"),
    ("soft-touch resin outer shell", "felt face surround", "powder-coated join"),
    ("textured paper-composite outer shell", "smoked glass face window", "rubber edge seam"),
    ("satin enamel outer shell", "knit fiber face surround", "anodized aluminum detail"),
    ("translucent acrylic outer shell", "matte silicone face plane", "woven cord join"),
    ("cork composite outer shell", "soft leather face surround", "brushed steel detail"),
    ("molded rubber outer shell", "linen face surround", "ceramic link"),
    ("matte wood composite outer shell", "felt face plane", "anodized aluminum detail"),
    ("woven textile outer shell", "porcelain face plane", "recycled resin join"),
)
_ART_DIRECTION = {
    "shelter": {
        "description": "A soft asymmetric companion that keeps a little pocket of calm open beside the user.",
        "form_metaphor": "a small nested keepsake wrap that has learned to walk beside someone",
        "body_grammar": "A low asymmetric cushion companion: a plump comma-shaped torso, one quilted side flap no taller than the body, two soft feet set at different heights, and a tiny flat stitched face directly on the body surface beside the seam, no larger than one third of the body height.",
        "silhouette_tokens": ["low comma-shaped cushion torso", "one short quilted side flap", "two offset soft feet", "tiny flat stitched face on body surface"],
        "relationship_gesture": "It scoots close, turns its wrap flap outward like a tiny invitation, and waits without asking to be picked up.",
        "tactile_hook": "A pinchable plush edge and one line of raised blanket stitching invite a calming thumb rub.",
        "signature_hook": "One ribbon-like pull tab is stitched into the outer shoulder seam, never placed at the body center.",
        "interaction_signature": "It scoots close and opens its wrapped shoulder into a small quiet invitation.",
        "board_composition": "Let the off-center shoulder flap create an asymmetrical reading path from hero to tactile seam details.",
    },
    "beacon": {
        "description": "A tiny purposeful companion that makes the next gentle move feel visible without becoming an instrument or a person in costume.",
        "form_metaphor": "a tiny felt courier with one little folded paper flag resting against its shoulder",
        "body_grammar": "A low pear-shaped felt companion that leans gently forward, with one small folded paper flag attached behind one shoulder and never taller than the body, two springy feet, and a simple non-human stitched face directly on the body surface, no larger than one third of the body height.",
        "silhouette_tokens": ["low pear-shaped felt body", "one small shoulder paper flag", "two springy feet", "small flat stitched face on body surface"],
        "relationship_gesture": "It takes one hopeful half-step, tips its little shoulder flag toward the user, then settles back to leave the next move feeling small.",
        "tactile_hook": "A soft pleated flag edge and a tiny stitched pull tab give the body an immediately hand-made feel.",
        "signature_hook": "One tiny folded star pennant is stitched along the high shoulder seam, never centered on the chest.",
        "interaction_signature": "It makes one hopeful half-step, tips its small shoulder flag toward the user, then settles back to make the next move feel small.",
        "board_composition": "Use the small shoulder flag as a gentle off-center reading cue, then resolve through the stitched shoulder detail and tiny feet.",
    },
    "bridge": {
        "description": "An uneven little tandem companion that makes room for two sides without splitting into two separate objects.",
        "form_metaphor": "an uneven little tandem held together by a woven loop, made to make room for two sides",
        "body_grammar": "An off-balance tandem companion: one taller rounded lobe and one smaller bean-like lobe joined by a visible woven loop, with a single small flat stitched face directly on the taller lobe's body surface, no larger than one third of the body height.",
        "silhouette_tokens": ["uneven paired body", "one taller rounded lobe", "one smaller bean-like lobe", "visible woven joining loop", "small flat stitched face on body surface"],
        "relationship_gesture": "The smaller half leans toward the larger one, then both turn slightly outward as though making space for the user to join them.",
        "tactile_hook": "A braided fabric joining loop and contrasting nap across the two halves make the connection readable by touch.",
        "signature_hook": "One visible woven loop joins the unequal halves off-center, never as a button or central light.",
        "interaction_signature": "The smaller half leans in, then both halves turn outward to make room for the user.",
        "board_composition": "Use a deliberately uneven paired composition that follows the woven loop from one half to the other.",
    },
}
_DEFAULT_FORM_AVOIDS = [
    "symmetric toy pod silhouette",
    "face trapped inside a shell or an oval face window",
    "central status light or center button",
    "armor plating or heroic mech proportions",
    "consumer electronics casing or appliance seams",
    "human child face, realistic skin, or a costumed-person silhouette",
    "face enclosed in a hood, helmet, cone, shell, or oval window",
    "oversized blade, sail, or wing taller than the body",
    "large separate face applique or dominant central face panel",
]
_DIRECTION_VARIANTS = {
    "shelter": (
        {
            "description": "A low companion that keeps a quiet center available while making space for the user to return to their own pace.",
            "form_metaphor": "A compact layered shelter with a soft face opening held inside one protected center.",
            "silhouette_tokens": ["low enclosing outer volume", "wide settled base", "small attentive face opening"],
            "palette_tokens": ["resting outer field", "quiet face-value opening", "one contained living accent"],
            "material_tokens": ["layered tactile outer shell", "matte inner face surface", "quiet structural joins"],
            "signature_hook": "One protected core becomes visible only at the companion's center.",
            "interaction_signature": "It settles near the user, softens the pace, and keeps one quiet working rhythm available.",
            "board_composition": "Use an inward evidence sequence: broad protective forms frame a quiet center, with details gathering toward it.",
            "anti_drift": ["no tomb or shrine", "no armored fortress", "no closed statue pose"],
        },
        {
            "description": "A small companion that creates a calm boundary around the user's attention without withdrawing from them.",
            "form_metaphor": "A folded, grounded form that opens just enough to reveal a responsive inner companion.",
            "silhouette_tokens": ["folded upper cover", "grounded lower mass", "responsive central aperture"],
            "palette_tokens": ["grounding field", "soft inner-value break", "one restrained core accent"],
            "material_tokens": ["soft structural layers", "matte face plane", "small protective fittings"],
            "signature_hook": "One inner signal is framed by the companion's opening rather than worn as decoration.",
            "interaction_signature": "It stays close without crowding, opening its center when the user needs room to regroup.",
            "board_composition": "Use a nested reading rhythm: an outer field yields to an attentive inner portrait and close material evidence.",
            "anti_drift": ["no burial object", "no solemn relic", "no static stone mascot"],
        },
        {
            "description": "A quiet companion whose stable body makes unfinished work feel safe to return to.",
            "form_metaphor": "A compact resting form with a protected inner face and one low, steady center of gravity.",
            "silhouette_tokens": ["soft enclosing top", "broad planted feet", "calm inner face zone"],
            "palette_tokens": ["soft resting field", "clear inner-value zone", "one held accent"],
            "material_tokens": ["tactile protective skin", "quiet matte face", "modular support seams"],
            "signature_hook": "One low internal marker anchors the body without becoming a separate prop.",
            "interaction_signature": "It waits patiently at the edge of the task and makes restarting feel smaller and safer.",
            "board_composition": "Use a low, settled composition: make the hero feel grounded, then reveal its protected center through close views.",
            "anti_drift": ["no temple guardian", "no heavy armor", "no inert sleeping object"],
        },
    ),
    "beacon": (
        {
            "description": "An upright companion that turns scattered attention into one calm, visible next direction.",
            "form_metaphor": "A compact standing guide with a small listening face beneath one aligned focus channel.",
            "silhouette_tokens": ["clear vertical body axis", "small forward face opening", "one contained focus channel"],
            "palette_tokens": ["supporting outer field", "clear face-value break", "one focused active accent"],
            "material_tokens": ["soft structured outer shell", "precise central fitting", "responsive focal detail"],
            "signature_hook": "One central signal aligns attention without becoming a separate tool or weapon.",
            "interaction_signature": "It pauses beside the user, gathers scattered attention, then offers one clear next direction.",
            "board_composition": "Use a vertical evidence route: move from the hero through one aligned focal detail into concise supporting views.",
            "anti_drift": ["no ceremonial crown", "no staff or weapon", "no religious icon"],
        },
        {
            "description": "A small companion that notices hesitation and helps turn intention into one manageable move.",
            "form_metaphor": "A balanced guide form with a quiet upper aperture and a compact body that leans gently forward.",
            "silhouette_tokens": ["tapered upper form", "compact forward body", "visible centerline"],
            "palette_tokens": ["supporting base field", "attentive face zone", "one directional accent"],
            "material_tokens": ["layered soft structure", "clean central join", "subtle translucent inset"],
            "signature_hook": "One narrow internal aperture appears when the companion is ready to help the user move forward.",
            "interaction_signature": "It notices hesitation, leans in quietly, and turns intention into a single next move.",
            "board_composition": "Use a forward reading sequence: establish the hero, then let each smaller panel clarify how its focus travels through the body.",
            "anti_drift": ["no fantasy priest", "no regal armor", "no floating magic effect"],
        },
        {
            "description": "A focused companion that holds one visible path without demanding the user's attention.",
            "form_metaphor": "A small upright companion with a calm face opening and one precise, body-integrated direction marker.",
            "silhouette_tokens": ["single upright volume", "balanced lower body", "clean central marker"],
            "palette_tokens": ["stable outer relationship", "readable face-value contrast", "one concise signal accent"],
            "material_tokens": ["matte layered shell", "small articulated join", "contained focal surface"],
            "signature_hook": "One body-integrated marker changes emphasis without adding a handheld prop.",
            "interaction_signature": "It stays at the edge of the user's work, keeping one path visible without asking to be the center of attention.",
            "board_composition": "Use a measured vertical grid with one dominant axis; keep supporting evidence calm so the focus mechanism remains legible.",
            "anti_drift": ["no wizard costume", "no shrine silhouette", "no oversized headpiece"],
        },
    ),
    "bridge": (
        {
            "description": "A companion that makes collaboration feel steady by holding two sides around one welcoming shared center.",
            "form_metaphor": "A compact paired form with two distinct side volumes joining at one open central face zone.",
            "silhouette_tokens": ["paired side volumes", "open central face zone", "stable shared base"],
            "palette_tokens": ["two balanced outer fields", "welcoming face-value center", "one connecting accent"],
            "material_tokens": ["tactile paired layers", "matte face surface", "small connecting hardware"],
            "signature_hook": "One visible connection joins the two sides only at the shared center.",
            "interaction_signature": "It turns two sides toward a shared center before inviting the user forward.",
            "board_composition": "Use paired evidence groups that meet at one shared center; let contrast describe relation rather than decoration.",
            "anti_drift": ["no headphone character", "no toy egg", "no generic robot pod"],
        },
        {
            "description": "A companion that holds difference gently enough for the user to keep moving with another person or task.",
            "form_metaphor": "A low linked companion whose two supporting forms leave a deliberate opening for an attentive central face.",
            "silhouette_tokens": ["two supportive side shells", "low shared footing", "clear central opening"],
            "palette_tokens": ["complementary outer relationship", "open face-value zone", "one mutual accent"],
            "material_tokens": ["paired tactile shells", "soft central face plane", "precise joining mechanism"],
            "signature_hook": "One joining mechanism becomes meaningful only when both sides are visible together.",
            "interaction_signature": "It makes room for two perspectives, then helps the user find a workable shared next step.",
            "board_composition": "Use a bilateral layout with an intentional center break; show each side alone before showing what their connection makes possible.",
            "anti_drift": ["no split personality mascot", "no decorative clasp only", "no novelty gadget"],
        },
        {
            "description": "A warm companion that keeps connection tangible without becoming overly cute or passive.",
            "form_metaphor": "A small relational form with two grounded halves and one clear center that welcomes approach.",
            "silhouette_tokens": ["rounded paired body", "grounded twin feet", "open shared center"],
            "palette_tokens": ["balanced paired fields", "welcoming light-value center", "one contained link accent"],
            "material_tokens": ["durable paired surfaces", "matte inner face", "small structural link"],
            "signature_hook": "One central link makes the pair read as a companion rather than two separate objects.",
            "interaction_signature": "It stays alongside the user, making connection feel tangible without taking over the task.",
            "board_composition": "Use a relationship map: alternate individual side details with shared-center evidence, then resolve in one unified hero.",
            "anti_drift": ["no baby toy form", "no symmetrical gadget", "no disconnected paired objects"],
        },
    ),
}


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


def _visual_relationships(direction: str, digest: str) -> tuple[list[str], list[str]]:
    """Return stable, public-safe color and finish relationships for one candidate."""
    seed = int(hashlib.sha256(f"visual-dna:{digest}".encode("utf-8")).hexdigest()[:8], 16)
    palette_index = (seed + _DIRECTION_OFFSET[direction]) % len(_PALETTE_RELATIONSHIPS)
    material_index = (seed // len(_PALETTE_RELATIONSHIPS) + _DIRECTION_OFFSET[direction]) % len(_MATERIAL_RELATIONSHIPS)
    return list(_PALETTE_RELATIONSHIPS[palette_index]), list(_MATERIAL_RELATIONSHIPS[material_index])


def _candidate(direction: str, rank: int, digest: str) -> dict[str, Any]:
    name = _NAME_PREFIX[int(digest[rank * 2:rank * 2 + 2], 16) % len(_NAME_PREFIX)]
    variant_index = int(hashlib.sha256(f"{direction}:{digest}".encode("utf-8")).hexdigest()[:8], 16) % len(_DIRECTION_VARIANTS[direction])
    definition = _DIRECTION_VARIANTS[direction][variant_index]
    art_direction = _ART_DIRECTION[direction]
    palette_tokens, material_tokens = _visual_relationships(direction, digest)
    return {
        "candidate_id": f"{direction}-{digest[:6]}-{rank + 1}",
        "ip_name": f"{name} {direction.title()}",
        "display_name": f"{name} / {direction.title()}",
        **definition,
        "description": art_direction["description"],
        "form_metaphor": art_direction["form_metaphor"],
        "silhouette_tokens": art_direction["silhouette_tokens"],
        "body_grammar": art_direction["body_grammar"],
        "relationship_gesture": art_direction["relationship_gesture"],
        "tactile_hook": art_direction["tactile_hook"],
        "signature_hook": art_direction["signature_hook"],
        "interaction_signature": art_direction["interaction_signature"],
        "board_composition": art_direction["board_composition"],
        "default_form_avoids": list(_DEFAULT_FORM_AVOIDS),
        "palette_tokens": palette_tokens,
        "material_tokens": material_tokens,
        "anti_drift": [
            "no literal animal",
            "no generic blob",
            "no scenery",
            "no detached effects",
            "keep the companion compact and emotionally present",
            *_DEFAULT_FORM_AVOIDS,
            *definition["anti_drift"],
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
        "compiler_version": 2,
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
