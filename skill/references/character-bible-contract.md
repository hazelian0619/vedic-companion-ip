# Board-First Candidate Contract

The portable candidate manifest is JSON with exactly three `candidates`. New production candidates must include the following visual-safe fields:

```json
{
  "candidate_id": "short-stable-slug",
  "ip_name": "Pet name",
  "display_name": "User-facing name",
  "description": "One visual-safe sentence",
  "form_metaphor": "Visual metaphor",
  "body_grammar": "Specific non-generic body construction",
  "silhouette_tokens": ["visual token"],
  "relationship_gesture": "How it makes contact with the user",
  "tactile_hook": "A material detail that invites touch",
  "palette_tokens": ["color relationship"],
  "material_tokens": ["material relationship"],
  "signature_hook": "Stable visual signature",
  "default_form_avoids": ["forbidden generic construction"],
  "interaction_signature": "Visual-safe companion behavior",
  "board_composition": "Character-led information reading direction",
  "anti_drift": ["visual constraint"]
}
```

The manifest is invalid if it contains personal data, chart terminology, source evidence, rationale, internal IDs, or unrecognized fields. Palette and material are local relationships, not a global product palette or style theme.

`body_grammar` must describe a character that can be recognized by silhouette and gesture, not only color or a central ornament. `default_form_avoids` must explicitly rule out symmetric toy pods, shell-trapped or oval face windows, central status lights/buttons, armor/mech proportions, and consumer-electronics casing.

Imagev2 first renders a non-canonical full-body hero from this contract. It then renders one text-bearing Identity Board using that hero as exact identity input. The board can use an optional user-supplied editorial reference as a second, style-only input. It is the only user-facing identity artifact.

After the user selects a board, Hatch receives only the locked `identity-hero.png` reference. Hatch creates the canonical base and all animation media. `identity-lock.json` records hero, board, copied Hatch reference, base hashes, and run location. There is no second post-selection Character Bible.

Historical Character Bible contracts and three-Hatch candidate runs are legacy-only. Do not use them for a new session.
