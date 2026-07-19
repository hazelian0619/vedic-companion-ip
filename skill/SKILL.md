---
name: vedic-companion-ip
description: Use when a user wants a privacy-preserving companion pet derived from locally computed birth-chart facts, needs three visual identity choices before a single Hatch production run, or wants to package the selected character as a Codex pet.
---

# Vedic Companion IP

Use this production order exactly:

```text
private local intake -> local chart facts -> 3 safe art-direction contracts
-> 3 non-canonical imagev2 heroes -> 3 text-bearing imagev2 Identity Boards
-> user chooses one board -> 1 official hatch-pet canonical base
-> official hatch-pet animation, QA, and package
```

Imagev2 owns exploration only. `hatch-pet` owns the selected canonical base, all animation rows, atlas, QA, and installable package. There is **no second post-selection Character Bible**. The Identity Board is the only user-facing board and contains the exact internal hero that Hatch receives.

## Hard Boundaries

- Keep birth date, time, place, coordinates, timezone, reports, chart terms, source evidence, and reasoning local. Do not put them in image prompts, safe candidates, boards, Git, or packages.
- Credentials are process-only environment variables. Never persist keys in prompts, manifests, shell history, or source.
- A new production candidate needs the full schema in [character-bible-contract.md](references/character-bible-contract.md), including body grammar, relationship gesture, tactile hook, and default-form avoids.
- The three boards must have distinct character grammars. Palette and material are secondary relationships, never the sole identity or a global style system.
- Do not ask Hatch to invent a character from abstract tokens. It must receive the selected `identity-hero.png` as its only reference.
- Do not select on the user's behalf. Stop after the three accepted boards until the user chooses one.

Set the installed directory once:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/vedic-companion-ip"
```

## Board-First Stage

Create the private session and three safe public candidates:

```bash
python3 "$SKILL_DIR/scripts/prepare_product_session.py" \
  --intake /absolute/path/to/private-birth-input.json \
  --session-dir /absolute/path/to/session
```

For every candidate ID in `safe-candidates.json`, render its hero first and then its Identity Board. `--design-reference` is optional and style-only; do not use it as character identity. Without it, the candidate contract chooses the appropriate editorial language without a fixed palette or layout.

```bash
python3 "$SKILL_DIR/scripts/render_identity_board_cli.py" \
  --session-dir /absolute/path/to/session \
  --candidate-id "<candidate-id>" \
  --api-key-env "<user-configured-key-variable>" \
  --image-base-url "https://provider.example/v1" \
  --design-reference /optional/path/to/editorial-reference.png
```

If an explicitly configured OpenAI-compatible provider can generate but its SDK `images.edit` transport is incompatible, append `--provider-http-fallback`. This is the same `gpt-image-2` endpoint and preserves the same hero-first request order. It is not a text-only redraw or model downgrade; credentials remain process-only.

Inspect each hero/board pair. Do not call the four flags unless the image actually passes all four checks:

```bash
python3 "$SKILL_DIR/scripts/record_identity_board_qa.py" \
  --session-dir /absolute/path/to/session \
  --candidate-id "<candidate-id>" \
  --reviewer "<human-or-visual-qa-agent>" \
  --note "<specific identity, typography, and completeness verdict>" \
  --identity-consistent \
  --art-direction-distinct \
  --typography-acceptable \
  --board-complete
```

After all three passing QA records exist:

```bash
python3 "$SKILL_DIR/scripts/record_identity_boards.py" \
  --session-dir /absolute/path/to/session
python3 "$SKILL_DIR/scripts/session_status.py" \
  --session-dir /absolute/path/to/session
```

Present only the three `identity_board` paths from `identity-boards.json` or `session_status.py`. The hero is an internal Hatch reference, not a separate choice screen.

## Choice And Hatch Production

When the user has selected one board, lock it before any Hatch generation:

```bash
python3 "$SKILL_DIR/scripts/select_identity_candidate.py" \
  --session-dir /absolute/path/to/session \
  --candidate-id "<selected-candidate-id>" \
  --decision "<user decision note>"
```

Only the selected candidate may enter Hatch production; the other two boards remain choice artifacts and never receive a base, rows, or package.

Prepare exactly one official Hatch run. Its only external identity image is the selected hero. The Hatch `auto` production preset may infer extraction-safe rendering from that exact reference, but it is never the artistic decision-maker.

```bash
python3 "$SKILL_DIR/scripts/prepare_selected_hatch_run.py" \
  --session-dir /absolute/path/to/session
```

Run the selected base job through the official imagegen CLI fallback only when the user has configured a provider environment variable:

```bash
python3 "$SKILL_DIR/scripts/hatch_base_cli.py" \
  --run-dir /absolute/path/to/session/selected-hatch/<candidate-id>/hatch-pet-run \
  --api-key-env "<user-configured-key-variable>" \
  --image-base-url "https://provider.example/v1"
```

Inspect that base against the selected hero, then create the immutable lock. This verifies the hero, board, copied Hatch reference, completed base job, and canonical base hashes:

```bash
python3 "$SKILL_DIR/scripts/record_selected_base.py" \
  --session-dir /absolute/path/to/session \
  --reviewer "<human-or-visual-qa-agent>" \
  --note "<specific identity-preservation verdict>"
```

Resolve the only run allowed to animate:

```bash
python3 "$SKILL_DIR/scripts/selected_hatch_run.py" \
  --session-dir /absolute/path/to/session
```

Use the installed `hatch-pet` Skill on that run only. Generate rows from its immutable `references/canonical-base.png`, run the official deterministic extraction, contact sheet, previews, visual QA, and then install:

```bash
python3 "$SKILL_DIR/scripts/record_visual_qa.py" \
  --run-dir /absolute/path/to/selected/hatch-pet-run \
  --reviewer "<human-or-visual-qa-agent>" \
  --note "<identity, gait, transparency, and state-semantics verdict>"
python3 "$SKILL_DIR/scripts/install_selected_pet.py" \
  --session-dir /absolute/path/to/session
```

## Failure Rules

- Missing or failed visual QA blocks `identity_boards_ready`.
- No user choice means no Hatch run, base, rows, or package.
- A changed hero, board, Hatch reference, or canonical base blocks the next stage.
- A completed base from any run other than the selected run is invalid.
- If identity drifts in a Hatch row, repair that row from the canonical base. Do not regenerate a new board or base.
- Legacy budget-preview path only: `prepare_candidate_runs.py`, `render_design_branch.py`, `render_character_bible_cli.py`, and `select_candidate.py` remain for historical sessions, not new production.

## Resources

- `identity_board.py`: visual-safe hero and Identity Board request builder.
- `scripts/render_identity_board_cli.py`: hero-first imagev2 rendering.
- `scripts/record_identity_board_qa.py` and `scripts/record_identity_boards.py`: visual acceptance and three-board gate.
- `scripts/select_identity_candidate.py`, `scripts/prepare_selected_hatch_run.py`, and `scripts/record_selected_base.py`: selected-only Hatch handoff and identity lock.
- `scripts/selected_hatch_run.py`: resolves either the new identity lock or a historical selected pair.
- `references/character-bible-contract.md`: portable safe-candidate and handoff contract.
