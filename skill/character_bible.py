"""Design-safe imagev2 prompt construction for Character Bible visuals."""
from __future__ import annotations

import json
from typing import Any

from board_system import resolve_board_system
from companion_ip_contract import astrology_term_scan, privacy_scan


_REQUIRED_FIELDS = frozenset(
    {
        "official_base_path",
        "ip_name",
        "display_name",
        "form_metaphor",
        "silhouette_tokens",
        "palette_tokens",
        "material_tokens",
        "signature_hook",
        "anti_drift",
    }
)

_BRANCH_REQUIRED_FIELDS = frozenset(
    {
        "board_reference_path",
        "hatch_seed_prompt",
        "ip_name",
        "display_name",
        "form_metaphor",
        "silhouette_tokens",
        "palette_tokens",
        "material_tokens",
        "signature_hook",
        "anti_drift",
    }
)


def _joined(values: list[str]) -> str:
    return ", ".join(" ".join(value.split()) for value in values)


def _validate_board_input(board_input: dict[str, Any]) -> None:
    if not _REQUIRED_FIELDS.issubset(board_input) or not (board_input.get("board_reference_path") or board_input.get("board_system")):
        raise ValueError("unsafe board input")
    visual_only = {
        key: value
        for key, value in board_input.items()
        if key not in {"official_base_path", "board_reference_path", "board_system"}
    }
    blob = json.dumps(visual_only, ensure_ascii=False)
    if privacy_scan(blob)[1] or astrology_term_scan(blob):
        raise ValueError("unsafe board input")


def build_visual_board_prompt(board_input: dict[str, Any]) -> str:
    """Return an imagev2 prompt for visual plates grounded in an official base."""
    _validate_board_input(board_input)
    if board_input.get("board_system"):
        system_prompt = resolve_board_system(str(board_input["board_system"]))["prompt"]
        type_direction = "Derive type contrast, copy color, divider treatment, and language mix from the official base and candidate; retain the chosen professional board system's hierarchy."
        arrangement_direction = "Arrange the required evidence using the selected professional board system; adapt section count, placement, rule treatment, and emphasis to this character."
    else:
        system_prompt = "Use input image 2 only as the user-approved editorial board-system reference. Derive the palette, background treatment, typography hierarchy, border language, information density, and panel rhythm from it; do not copy its character."
        type_direction = "Derive type contrast, copy color, divider treatment, and language mix from input image 2."
        arrangement_direction = "Arrange the required evidence according to input image 2's information architecture."
    return f"""Use case: stylized-concept
Asset type: finished premium Character Bible, an information-rich but not crowded 1:1 collectible-character specification board.
Input image 1: official canonical base. Preserve this exact pet identity in every view. Do not redesign its species, silhouette, face, palette relationship, materials, or signature object.
{system_prompt}

Primary request: Create one finished 1024x1024 Character Bible for {board_input['display_name']}. Render legible integrated typography as part of the image, not placeholder glyphs. {type_direction}

Required information groups: identity, signature, turnaround, silhouette and body-ratio rules, palette, material language, expression strip, motion/state strip, technical material callouts, scale-readability check, and must-preserve rules. Render concise headings and short callouts only; do not use paragraphs, force a fixed language, title list, or typography system across users.

Board content: arrange a hero, turnaround views, proportion diagram, expression crops, motion/state poses, material close-ups, palette, scale-readability check, and must-preserve information. {arrangement_direction} All views must visibly be the same official canonical base character.
Subject: {board_input['form_metaphor']}. Silhouette: {_joined(board_input['silhouette_tokens'])}. Palette: {_joined(board_input['palette_tokens'])}. Materials: {_joined(board_input['material_tokens'])}. Signature object: {board_input['signature_hook']}.
Constraints: preserve the official canonical base; keep all copy concise and readable; do not redesign the character; { _joined(board_input['anti_drift']) }.
Avoid: astrology symbols, charts, planets, birth data, logos, watermarks, scenery, detached effects, additional characters, low-contrast text, garbled glyphs, empty panels, or generic toy-product presentation."""


def build_render_request(board_input: dict[str, Any]) -> dict[str, Any]:
    """Create an imagev2 request with explicit identity and board-style roles."""
    _validate_board_input(board_input)
    return {
        "prompt": build_visual_board_prompt(board_input),
        "reference_paths": [board_input["official_base_path"]] + ([board_input["board_reference_path"]] if board_input.get("board_reference_path") else []),
    }


def _validate_branch_input(branch_input: dict[str, Any]) -> None:
    if not _BRANCH_REQUIRED_FIELDS.issubset(branch_input):
        raise ValueError("unsafe design branch input")
    candidate_only = {
        key: value
        for key, value in branch_input.items()
        if key not in {"board_reference_path", "hatch_seed_prompt"}
    }
    candidate_blob = json.dumps(candidate_only, ensure_ascii=False)
    seed_blob = str(branch_input["hatch_seed_prompt"])
    if (
        privacy_scan(candidate_blob)[1]
        or astrology_term_scan(candidate_blob)
        or privacy_scan(seed_blob)[1]
    ):
        raise ValueError("unsafe design branch input")


def build_design_branch_request(branch_input: dict[str, Any]) -> dict[str, Any]:
    """Build imagev2 branch requests from a prepared official hatch seed."""
    _validate_branch_input(branch_input)
    seed = " ".join(str(branch_input["hatch_seed_prompt"]).split())
    board_prompt = f"""Use case: stylized-concept
Asset type: finished text-bearing Character Bible design branch for a Codex companion pet.
Input image 1: user-approved Character Bible editorial reference. Derive the visual system, palette, typography hierarchy, language mix, information density, and panel rhythm from this reference. Do not copy its character or impose a product-wide style.

Official hatch-pet seed (authoritative identity source): {seed}

Primary request: Create one finished 1024x1024 Character Bible for {branch_input['display_name']}. Render legible integrated typography, headings, captions, palette labels, material notes, body-ratio notes, and must-preserve notes as part of the image. The board must include a hero, turnaround, expression strip, motion/state strip, material close-ups, palette, scale-readability check, and must-preserve rules. Match the editorial reference's information architecture while preserving this candidate's own identity.
Subject: {branch_input['form_metaphor']}. Silhouette: {_joined(branch_input['silhouette_tokens'])}. Palette roles: {_joined(branch_input['palette_tokens'])}. Materials: {_joined(branch_input['material_tokens'])}. Signature object: {branch_input['signature_hook']}.
Constraints: keep copy concise and readable; { _joined(branch_input['anti_drift']) }.
Avoid: astrology symbols, charts, planets, birth data, logos, watermarks, scenery, detached effects, additional characters, low-contrast text, garbled glyphs, empty panels, or generic toy-product presentation."""
    identity_reference_prompt = f"""Use case: stylized-concept
Asset type: clean full-body identity reference for an official hatch-pet base job.
Input image 1: the just-rendered Character Bible design board. It is the sole visual lineage source for this image. Extract the exact same character from its hero and turnaround views; preserve its silhouette, face window, body ratios, palette relationships, material treatment, and signature object. Do not reinterpret it as a new character or use it merely as an editorial-style reference.

Official hatch-pet seed (authoritative identity source): {seed}

Primary request: Render one centered full-body reference of {branch_input['display_name']} extracted from that exact board. Preserve: {branch_input['form_metaphor']}; silhouette {_joined(branch_input['silhouette_tokens'])}; signature {branch_input['signature_hook']}; materials {_joined(branch_input['material_tokens'])}. Keep the figure compact and fully visible, with generous padding and a simple neutral studio background. No text, no labels, no board layout, no scenery, no extra characters, and no detached effects."""
    return {
        "board_prompt": board_prompt,
        "identity_reference_prompt": identity_reference_prompt,
        "reference_paths": [str(branch_input["board_reference_path"])],
        "output_roles": ["board", "identity_reference"],
    }
