---
name: vedic-companion-ip
description: Create a privacy-preserving companion-pet experience from locally computed birth-chart facts. Use when a user wants three candidate pet IPs, official hatch-pet animation packaging, and an imagev2 Character Bible without sending birth data, chart language, or internal rationale to image generation.
---

# Vedic Companion IP

Build a companion pet in this fixed order:

```text
private intake -> local deterministic chart provider -> three visual-safe candidate contracts
-> three official hatch-pet canonical bases -> three imagev2 Character Bibles
-> user selects one base/board pair -> official hatch-pet rows, QA, and Codex package
```

The astrology provider is local only. This Skill drafts three visual-safe candidates
with an LLM from de-identified chart facts (when a local Vedic runtime and an
image-API provider are configured), then gates them through `candidate_validator`.
It does not replace the installed `hatch-pet` Skill. Official `hatch-pet` owns
every canonical base and animation row. Imagev2 may render Character Bibles only
from an accepted official base.

## Step 0 — Preflight (onboarding)

Before any run, verify the environment and auto-install anything missing. The
agent reads the output and guides the user through any gap before continuing:

```bash
python3 "$SKILL_DIR/scripts/preflight.py"
```

preflight detects VEDIC_PY, the official `hatch-pet` skill, the `imagegen`
system skill, and the image-API credentials in the user's process environment.
With `--auto-install` (default) it installs VEDIC_PY into a scoped skill-local
venv and clones `hatch-pet` when `HATCH_PET_REPO` is set; it verifies the image
API with a live `/v1/models` call. Credentials are read from process env only
and are never printed or written. `--check` is read-only for CI. If any
required dependency is missing, preflight exits non-zero (fail-closed) and the
flow stops here.

The user sets the image API in their OWN process environment (never in a file):
```bash
export IMAGEV2_API_KEY='sk-...'        # user's key; never commit
export IMAGEV2_ENDPOINT='https://tok.fan/v1'
export IMAGEN_MODEL='gpt-image-2'
```

## Privacy Gate

Keep private inputs and reasoning local: birth dates, times, locations, coordinates, timezones, chart reports, chart terms, and candidate rationale never enter an image request or a portable candidate manifest.

Accept only the schema in [character-bible-contract.md](references/character-bible-contract.md). Stop when a candidate contains an unrecognized field or a privacy/chart term. Do not use a raw contract JSON as input merely because it also contains visual fields.

Credentials are process-only environment variables. Do not write them to `.env`, source code, manifests, prompts, reports, shell history, or generated images.

Treat the session directory as the only orchestration boundary. Do not hand-write
`candidate-runs.json`, `candidate-bases.json`, `candidate-boards.json`, or
`selection.json`: the bundled commands create each artifact, hash it, and move
the session through its next permitted state.

## Candidate Stage

Set the installed Skill directory once for all bundled runners:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/vedic-companion-ip"
```

1. Create a product session. This runs local deterministic chart computation
   (VEDIC_PY: PyJHora + Swiss Ephemeris), enforces owner-only private outputs
   (0o600), writes the private chart-report and the de-identified pet-profile,
   and stops at `chart_ready`. It is credential-free:

```bash
python3 "$SKILL_DIR/scripts/prepare_product_session.py" \
  --intake /absolute/path/to/private-birth-input.json \
  --session-dir /absolute/path/to/session
```

2. Draft three visual-safe candidates with the LLM and gate them. `author_candidates.py`
   reads the de-identified pet-profile (ONLY `design_safe_evidence` — raw birth
   data, coordinates, timezone, and rationale in the profile are never sent),
   calls an OpenAI-compatible LLM guided by the
   [candidate-authoring-framework](references/candidate-authoring-framework.md) to
   draft three genuinely distinct directions, preserves a private draft, then
   hands them to `candidate_validator` — the hard gate (schema whitelist +
   privacy scan + astrology-term scan, fail-closed; rejects non-distinct
   directions). It records the public `safe-candidates.json` + a private evidence
   ledger and advances to `candidates_ready`:

```bash
python3 "$SKILL_DIR/scripts/author_candidates.py" \
  --session-dir /absolute/path/to/session \
  --api-key-env IMAGEV2_API_KEY \
  --llm-base-url "https://tok.fan/v1/chat/completions" \
  --llm-model "gpt-5.5"
```

The drafting-LLM provider is configurable (`--llm-base-url`, `--llm-model`,
`--api-key-env`) so a privacy-conscious user can point it at a local model. The
candidate TEXT the LLM returns is untrusted and is gated before any of it becomes
public or reaches the image model. If the gate rejects the draft, the session
stays at `chart_ready`; the private draft is preserved for inspection, and
`validate_candidates.py` can re-validate an edited draft without re-calling the LLM.

3. Each stable identity decision needs independent local evidence, but evidence and rationale remain private. The public candidate carries a safe interaction signature, board-composition direction, and stable individual color/material relationships: use them to differentiate how the companion helps and how its evidence is read. These are individual design results, not a product-wide palette, material, mascot species, or decorative motif.
4. Prepare exactly three official Hatch runs inside that session without generating images:

```bash
python3 "$SKILL_DIR/scripts/prepare_candidate_runs.py" \
  --session-dir /absolute/path/to/session
```

5. For each candidate, use the installed official `hatch-pet` workflow to generate and visually accept its canonical base before any imagev2 board. Its `pet_request.json`, base prompt, and state geometry define the animatable character boundary.

Before a CLI fallback base attempt, verify the official imagegen CLI is configured. This check never exposes credentials and does not claim that a key is valid until a real generation request succeeds:

```bash
python3 "$SKILL_DIR/scripts/imagegen_preflight.py"
```

When the user supplies an OpenAI-compatible image provider, they configure its key in their own process environment and may supply its endpoint at invocation time. Never place a key in a prompt, session file, report, or command history. The official Hatch base runner consumes only the environment variable name and the endpoint:

```bash
python3 "$SKILL_DIR/scripts/hatch_base_cli.py" \
  --run-dir /absolute/path/to/session/candidate-runs/<candidate-id>/hatch-pet-run \
  --api-key-env "<user-configured-key-variable>" \
  --image-base-url "https://provider.example/v1"
```

After all three bases have been generated and visually accepted, record exactly
those session-owned official bases. This is the required handoff from Hatch base
generation to Character Bible rendering:

```bash
python3 "$SKILL_DIR/scripts/record_candidate_bases.py" \
  --session-dir /absolute/path/to/session \
  --base "<candidate-a>=/absolute/path/to/session/candidate-runs/<candidate-a>/hatch-pet-run/references/canonical-base.png" \
  --base "<candidate-b>=/absolute/path/to/session/candidate-runs/<candidate-b>/hatch-pet-run/references/canonical-base.png" \
  --base "<candidate-c>=/absolute/path/to/session/candidate-runs/<candidate-c>/hatch-pet-run/references/canonical-base.png" \
  --reviewer "<human-or-visual-qa-agent>" \
  --note "<specific identity and animation-readiness verdict>"
```

6. Render one text-bearing imagev2 Character Bible from each accepted official base. The official base is the only identity authority; the board may document it but must never redesign it. The default `professional-editorial-v3` board system is a character-free, source-traceable layout contract: Swiss information design, industrial design review, and museum collection documentation. Use each candidate's board-composition direction to alter hierarchy and reading sequence rather than applying one generic catalog grid; show a `before -> response -> resolve` behavior proof as part of the board. It does not impose a fixed palette, material, typeface, or character. It rejects provider-unsafe prompt lengths locally before an image call.

```bash
python3 "$SKILL_DIR/scripts/render_character_bible_cli.py" \
  --session-dir /absolute/path/to/session \
  --candidate-id "<candidate-id>" \
  --out /absolute/path/to/session/candidates/<candidate-id>/character-bible.png \
  --api-key-env "<user-configured-key-variable>" \
  --image-base-url "https://provider.example/v1"
```

Visually inspect each rendered board before it becomes selectable. Confirm that every view keeps the canonical identity, all required information groups are present, and headings/captions are readable rather than placeholder or garbled glyphs. Record that acceptance for each candidate:

```bash
python3 "$SKILL_DIR/scripts/record_character_bible_qa.py" \
  --session-dir /absolute/path/to/session \
  --candidate-id "<candidate-id>" \
  --board /absolute/path/to/session/candidates/<candidate-id>/character-bible.png \
  --reviewer "<human-or-visual-qa-agent>" \
  --identity-consistent \
  --typography-acceptable \
  --layout-complete \
  --note "<specific visual acceptance note>"
```

Run it once per candidate, then record exactly the three matching base/board/QA triples before presenting choices:

```bash
python3 "$SKILL_DIR/scripts/record_candidate_boards.py" \
  --session-dir /absolute/path/to/session \
  --board "<candidate-a>=/absolute/path/to/session/candidates/<candidate-a>/character-bible.png" \
  --board "<candidate-b>=/absolute/path/to/session/candidates/<candidate-b>/character-bible.png" \
  --board "<candidate-c>=/absolute/path/to/session/candidates/<candidate-c>/character-bible.png" \
  --qa "<candidate-a>=/absolute/path/to/session/candidates/<candidate-a>/character-bible-qa.json" \
  --qa "<candidate-b>=/absolute/path/to/session/candidates/<candidate-b>/character-bible-qa.json" \
  --qa "<candidate-c>=/absolute/path/to/session/candidates/<candidate-c>/character-bible-qa.json"
```

The three base/board pairs are selection artifacts. Do not generate rows for any unselected candidate.

## Selection Gate

Show the three text-bearing Character Bibles with their matching official bases to the user. Only the selected candidate's base/board pair may continue. Record both the candidate decision and base acceptance before generating rows.

```bash
python3 "$SKILL_DIR/scripts/select_candidate.py" \
  --session-dir /absolute/path/to/session \
  --candidate-id "<selected-candidate-id>" \
  --base /absolute/path/to/session/candidate-runs/<selected-candidate-id>/hatch-pet-run/references/canonical-base.png \
  --board /absolute/path/to/session/candidates/<selected-candidate-id>/character-bible.png \
  --decision "<user acceptance reason>"
```

Resolve the immutable selected run before assigning any Hatch row jobs. This checks the selection/base/board hashes and returns only public artifact paths:

```bash
python3 "$SKILL_DIR/scripts/selected_hatch_run.py" \
  --session-dir /absolute/path/to/session
```

## Hatch Stage

Resume the selected official run with the installed `hatch-pet` Skill:

1. Resume the selected candidate's existing official Hatch run. Its accepted `references/canonical-base.png` is immutable identity authority; do not derive a replacement base from the Character Bible.
2. Generate `idle` and `running-right` with the canonical base and state layout guide attached. Inspect identity and gait.
3. Mirror `running-left` only when the official hatch-pet rules and visual inspection approve it. Otherwise generate it normally.
4. Generate the other app states from the same canonical base.
5. Run the official deterministic extraction, inspection, atlas composition, validation, contact-sheet, preview, and visual-QA steps.
6. After inspecting the contact sheet and all nine previews, record the explicit visual verdict:

```bash
python3 "$SKILL_DIR/scripts/record_visual_qa.py" \
  --run-dir /absolute/path/to/selected/hatch-pet-run \
  --reviewer "<human-or-visual-qa-agent>" \
  --note "<identity, gait, transparency, and state-semantics verdict>"
```

7. Install only after deterministic and visual QA pass. This command rechecks the selection hashes and will refuse an existing pet package rather than overwrite it:

```bash
python3 "$SKILL_DIR/scripts/install_selected_pet.py" \
  --session-dir /absolute/path/to/session
```

Keep `pet.json`, `spritesheet.webp`, validation JSON, contact sheet, all previews, frame review, visual QA, and QA summary.

## Failure Rules

- No official base: do not render a Character Bible.
- A base outside its recorded Hatch run, or one whose base job is incomplete: do not record it or render from it.
- Identity drift in a Character Bible: regenerate the board with the official base; never change the base to fit the board.
- Identity drift in an animation row: repair only that row using the canonical base.
- No user selection: stop after the three candidate boards. Do not produce three full atlases.
- Any privacy-gate failure: stop before any external call.

## Resources

- `scripts/preflight.py`: onboarding — detects + auto-installs VEDIC_PY/hatch-pet, verifies the image API for real; fail-closed on missing.
- `scripts/prepare_product_session.py`: credential-free local chart compute; writes private chart-report + de-identified pet-profile; stops at chart_ready.
- `scripts/author_candidates.py`: drafts 3 candidates via an OpenAI-compatible LLM from de-identified facts only; preserves a private draft; hands off to the validator.
- `candidate_validator.py`: the hard gate — schema whitelist + privacy/astrology scan + 3-distinct-directions; records public safe-candidates.json + private ledger; advances to candidates_ready.
- `scripts/validate_candidates.py`: ad-hoc re-validate+record of a draft JSON (no LLM call).
- `scripts/prepare_candidate_runs.py`: validates three safe candidates and scaffolds three official hatch-pet seed runs without generating images.
- `scripts/record_candidate_bases.py`: accepts exactly the three completed, session-owned official canonical bases before Character Bible rendering.
- `scripts/compute_chart_report.py`: local PyJHora/Swiss Ephemeris computation used by the product-session entry; requires the configured `VEDIC_PY` runtime.
- `scripts/imagegen_preflight.py`: redaction-safe configuration check for the official imagegen CLI fallback.
- `scripts/hatch_base_cli.py`: runs one official Hatch base job against a user-configured OpenAI-compatible provider without persisting credentials.
- `scripts/render_character_bible_cli.py`: uses official imagegen CLI `edit` with exactly one canonical-base image and the character-free professional board system.
- `scripts/record_character_bible_qa.py`: records identity, typography, and layout acceptance against the exact base/board hashes before a board can become selectable.
- `scripts/record_candidate_boards.py`: hashes and records exactly three accepted base/board pairs, then advances the selection gate.
- `scripts/selected_hatch_run.py`: resolves only the selected, hash-locked official Hatch run before animation.
- `scripts/record_board_provenance.py`: appends a public correction when an already-rendered board's source metadata needs repair; it never changes selection state.
- `scripts/record_visual_qa.py`: records the required explicit visual acceptance after all Hatch QA media exists.
- `scripts/install_selected_pet.py`: atomically installs only a selected, hash-locked, fully verified Hatch package.
- `scripts/session_status.py`: returns a redaction-safe public state and next action for external callers.
- `scripts/verify_delivery.py`: fails closed unless the Hatch atlas, validation, contact sheet, preview, and install pair all exist.
- `scripts/select_candidate.py`: locks the selected candidate/base/board pair by hash before animation.
- `scripts/render_character_bible.py`: legacy Chat Completions transport; do not use with an image provider that supports only `images/edits`.
- `scripts/render_design_branch.py` and `scripts/prepare_selected_hatch_run.py`: legacy budget-preview path only; do not use for the production Hatch-first path.
- `references/character-bible-contract.md`: portable input and handoff contract.
- `references/candidate-authoring-framework.md`: the standardized thinking for deriving three distinct directions from chart signals.
