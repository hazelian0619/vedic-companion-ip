"""Build privacy-safe hero and Identity Board prompts for Board-first production."""
from __future__ import annotations

import json
from typing import Any

from companion_ip_contract import astrology_term_scan, privacy_scan


_REQUIRED_FIELDS = frozenset(
    {
        "ip_name",
        "display_name",
        "form_metaphor",
        "body_grammar",
        "silhouette_tokens",
        "relationship_gesture",
        "tactile_hook",
        "palette_tokens",
        "material_tokens",
        "signature_hook",
        "default_form_avoids",
        "anti_drift",
    }
)
_PROVIDER_SAFE_PROMPT_CHARS = 3800


def _joined(values: list[str]) -> str:
    return ", ".join(" ".join(str(value).split()) for value in values)


def _avoidances(identity_input: dict[str, Any]) -> str:
    values = [*identity_input["default_form_avoids"], *identity_input["anti_drift"]]
    return _joined(list(dict.fromkeys(values)))


def _validate(identity_input: dict[str, Any]) -> None:
    if not _REQUIRED_FIELDS.issubset(identity_input):
        raise ValueError("unsafe identity board input")
    visual_only = {key: value for key, value in identity_input.items() if key != "design_reference_path"}
    blob = json.dumps(visual_only, ensure_ascii=False)
    if privacy_scan(blob)[1] or astrology_term_scan(blob):
        raise ValueError("unsafe identity board input")
    if any(not identity_input[field] for field in _REQUIRED_FIELDS):
        raise ValueError("unsafe identity board input")


def build_identity_board_requests(identity_input: dict[str, Any]) -> dict[str, object]:
    """Return hero-first imagev2 requests; the board may only document that hero."""
    _validate(identity_input)
    design_reference_path = str(identity_input.get("design_reference_path", ""))
    board_style_direction = (
        "Input image 2 is an editorial style-only reference. Borrow only its professional information-design method; never copy its character, background color, palette, metallic ornament, iconography, panel placement, typography styling, layout, or fixed visual theme."
        if design_reference_path
        else "Choose an editorial information-design treatment that arises from this character; do not impose a house palette, a fixed card grid, or a product-wide template."
    )
    avoidances = _avoidances(identity_input)
    hero_prompt = f"""Use case: stylized-concept
Asset type: one full-body non-canonical identity exploration for a gentle digital companion.
Let material, visual language, and framing arise from this character contract; do not borrow another character's body, face, palette, or costume.

Primary request: Design {identity_input['display_name']} as a specific, irresistibly endearing character with a readable silhouette at small scale. This is a non-canonical identity exploration, not a Hatch production base. Body grammar: {identity_input['body_grammar']} Form metaphor: {identity_input['form_metaphor']}. Silhouette: {_joined(identity_input['silhouette_tokens'])}. Relationship gesture: {identity_input['relationship_gesture']} Tactile hook: {identity_input['tactile_hook']}. Palette relationships: {_joined(identity_input['palette_tokens'])}. Material relationships: {_joined(identity_input['material_tokens'])}. Signature detail: {identity_input['signature_hook']}.

Show the whole character, centered with generous breathing room, in one warm expressive pose that demonstrates the relationship gesture. Make the asymmetry, tiny feet, and hand-made tactility visibly intentional. The face must be a small flat stitched mark directly on the body surface, never larger than one third of the body height and never a separate face patch, screen, or product indicator; never a human child face, realistic skin, a person in costume, or a hooded figurine.

Avoid: {avoidances}; literal animals, generic mascot expressions, scenery, detached effects, labels, typography, logos, watermarks, astrology symbols, charts, planets, birth data, or extra characters."""
    board_prompt = f"""Use case: stylized-concept
Asset type: one finished, text-bearing 1:1 Identity Board with integrated legible typography.
Use input image 1 as the exact hero identity for {identity_input['display_name']}. Preserve that exact character in every view: the same asymmetrical body grammar, face placement, proportions, materials, palette relationships, tiny feet, and signature detail. Do not invent a replacement character, do not merely use it as a mood reference, and do not make a second version of the hero.
{board_style_direction}

Primary request: Create one concise production Identity Board that helps a person choose this companion. Render legible integrated typography, never placeholder glyphs. This is not a brand campaign, marketing page, corporate values sheet, website, poster, or presentation. Use one dominant full-body hero; four small identity specimens showing front, side, back or 3/4, and relationship gesture; two tactile/material close-ups; a compact palette relationship note; and three concise must-preserve rules. Let the hero's own geometry determine the board composition; do not force a uniform set of tiles or fixed color system. Use only five short labels: NAME, FORM, GESTURE, TACTILE, and KEEP. Do not write paragraphs, slogans, mission statements, care guides, role or nature lists, URLs, domains, trademark marks, social proof, corporate icons, or generic value claims.

Identity facts to document: body grammar {identity_input['body_grammar']}; relationship gesture {identity_input['relationship_gesture']}; tactile hook {identity_input['tactile_hook']}; signature detail {identity_input['signature_hook']}. The board is the only user-facing identity artifact; keep it warm, precise, and visually generous.

Avoid: {avoidances}; redesigning the hero, generic toy-product presentation, garbled glyphs, low-contrast text, empty panels, scenery, detached effects, additional characters, logos, watermarks, URLs, domains, trademarks, corporate branding, astrology symbols, charts, planets, or birth data."""
    if max(len(hero_prompt), len(board_prompt)) > _PROVIDER_SAFE_PROMPT_CHARS:
        raise ValueError("identity board prompt exceeds the provider-safe limit")
    return {
        "hero_prompt": hero_prompt,
        "board_prompt": board_prompt,
        "hero_reference_paths": [],
        "board_reference_roles": ["hero"] + (["style_only"] if design_reference_path else []),
    }
