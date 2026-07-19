"""Named, character-free editorial systems for Character Bible generation."""
from __future__ import annotations


_SYSTEMS = {
    "professional-editorial-v2": {
        "sources": "International Typographic Style for modular grid discipline and hierarchy; museum collection documentation for evidence captions, scale, and material notation; production character bible practice for turnarounds, expression, motion, and preservation locks.",
        "prompt": """Board system: professional editorial specimen dossier. Source foundations: International Typographic Style, museum collection documentation, and production character bible practice. Build an asymmetric modular grid with a decisive reading sequence: identity and archival title, one dominant hero, then progressively smaller evidence views. Use a compact turnaround band, proportion and silhouette diagrams, a concise expression strip, a state strip, material close-ups, palette relationships, a scale-readability check, and a must-preserve lock panel. Let captions behave like object documentation: precise, short, aligned to what they describe. Keep the board information-rich but not crowded: use short display headings and short callouts, do not use paragraph copy, and leave intentional white space around the hero and every evidence group. Use an intentional display-to-annotation type hierarchy, consistent baseline alignment, and measured divider lines. Derive the palette relationships, material treatment, visual density, and type contrast from the official base and candidate. Do not inherit a house palette, a house material, a house typeface, a reference character, or a fixed number of panels.""",
    },
    "professional-editorial-v3": {
        "sources": "Swiss information design for alignment, indexing, and typographic hierarchy; industrial design review boards for orthographic evidence, scale, and construction constraints; museum collection documentation for short source-tied captions and material notation.",
        "prompt": """Board system: professional character-evidence monograph. Source foundations: Swiss information design, industrial design review, and museum collection documentation. Treat the board as an editorial argument, not a catalog page: its macro-composition echoes the candidate's relationship of forms and reading direction. Use one dominant hero plus three irregular, disciplined clusters, never a uniform set of tiles: behavioral proof (before, response, resolve), structural proof (turnaround, silhouette, body ratio, scale, signature), and preservation proof (materials, palette relationships, expression range, must-preserve locks).

Use a measured grid, baseline alignment, restrained dividers, and short callouts beside the exact view they explain. Derive the palette, background, type contrast, line treatment, density, cropping, and language mix from the official base and candidate. Do not impose a house palette, house material, house typeface, house character, house background, or fixed panel count. Keep it information-rich but not crowded: do not use paragraph copy; preserve negative space. Avoid a generic left biography column, evenly spaced product-card matrix, universal white paper background, and decorative swatches without an explanatory job.""",
    },
}


def resolve_board_system(name: str) -> dict[str, str]:
    try:
        return _SYSTEMS[name]
    except KeyError as error:
        raise ValueError(f"unknown board system: {name}") from error
