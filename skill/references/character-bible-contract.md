# Character Bible Contract

The portable candidate manifest is JSON with exactly three `candidates`. A candidate may contain only:

```json
{
  "candidate_id": "short-stable-slug",
  "ip_name": "Pet name",
  "display_name": "User-facing name",
  "description": "One visual-safe sentence",
  "form_metaphor": "Visual metaphor",
  "silhouette_tokens": ["visual token"],
  "palette_tokens": ["visual token"],
  "material_tokens": ["visual token"],
  "signature_hook": "Stable visual signature",
  "interaction_signature": "Visual-safe companion behavior",
  "board_composition": "Visual-safe information reading direction",
  "anti_drift": ["visual constraint"]
}
```

The compiler emits every field above. For legacy validated candidate manifests only, `interaction_signature` and `board_composition` may be omitted; the runner keeps backward compatibility but new production candidates must provide both. The manifest is invalid if it contains personal data, chart terminology, source evidence, rationale, internal IDs, or fields beyond this schema.

For the pre-hatch imagev2 design branch, use the safe candidate fields, the official hatch seed identity fields, and one user-approved Character Bible board reference. Generate the branch board first, then generate its identity reference from that board as the only image input.

For the production Character Bible, use only the accepted official base and these candidate fields. Reference order is mandatory:

1. official `references/canonical-base.png`, identity authority and sole image input

The default `professional-editorial-v3` board system has three professional language sources: Swiss information design for hierarchy, industrial design review for structural proof, and museum collection documentation for concise evidence captions. It is a layout contract, not a visual reference image: derive colors, materials, contrast, and language mix from the canonical base and candidate; never impose a product-wide palette, material, typeface, or visual style. Its three evidence groups are behavioral proof (`before -> response -> resolve`), structural proof, and identity-preservation proof. Ask imagev2 to render the integrated text-bearing board. Never ask it to render private data, chart language, or raw reasoning; the renderer rejects a provider-unsafe prompt locally, and visual QA must still confirm legibility.

Before selection, record a public Character Bible QA artifact for every candidate. It must match the exact canonical-base and board SHA-256 values and attest that identity is consistent, typography is readable, and the required information groups are complete. A missing, failed, or hash-mismatched QA artifact blocks the board from the selection manifest.
