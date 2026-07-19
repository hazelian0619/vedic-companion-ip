"""Named, character-free editorial systems for Character Bible generation."""
from __future__ import annotations


_SYSTEMS = {
    "professional-editorial-v2": {
        "sources": "International Typographic Style for modular grid discipline and hierarchy; museum collection documentation for evidence captions, scale, and material notation; production character bible practice for turnarounds, expression, motion, and preservation locks.",
        "prompt": """Board system: professional editorial specimen dossier. Source foundations: International Typographic Style, museum collection documentation, and production character bible practice. Build an asymmetric modular grid with a decisive reading sequence: identity and archival title, one dominant hero, then progressively smaller evidence views. Use a compact turnaround band, proportion and silhouette diagrams, a concise expression strip, a state strip, material close-ups, palette relationships, a scale-readability check, and a must-preserve lock panel. Let captions behave like object documentation: precise, short, aligned to what they describe. Keep the board information-rich but not crowded: use short display headings and short callouts, do not use paragraph copy, and leave intentional white space around the hero and every evidence group. Use an intentional display-to-annotation type hierarchy, consistent baseline alignment, and measured divider lines. Derive the palette relationships, material treatment, visual density, and type contrast from the official base and candidate. Do not inherit a house palette, a house material, a house typeface, a reference character, or a fixed number of panels.""",
    }
}


def resolve_board_system(name: str) -> dict[str, str]:
    try:
        return _SYSTEMS[name]
    except KeyError as error:
        raise ValueError(f"unknown board system: {name}") from error
