# Vedic Companion IP

> Your birth chart, computed locally, becomes one desktop companion — matched to your chart, locked across every state, never sent onward.

[![CI](https://github.com/hazelian0619/vedic-companion-ip/actions/workflows/ci.yml/badge.svg)](https://github.com/hazelian0619/vedic-companion-ip/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Vedic Companion IP turns your birth chart into a self-adaptively matched desktop companion.** The chart is computed locally with PyJHora + Swiss Ephemeris and never leaves your machine. What returns is one companion — silhouette, palette, and gait locked across nine animation states — authored from your chart's specifics, not a template, and never re-derived.

## What makes it different

- **Self-adaptive, not templated** — de-identified chart facts drive the companion's materials, palette, stance, and one authored signature. The outcome (endearing, tactile, quietly playful) is fixed; the chart shapes the specifics.
  - Facts that drive it: ascendant; each planet's sign / house / retrograde / dignity; Moon's nakshatra; dasha lord; atmakaraka. A generic mascot is a failure even if it is cute.
- **One companion, locked — not a one-shot image.** Silhouette, palette, and gait stay identical across nine animation states. Identity drift is repaired from the canonical base, never redrawn from scratch.
- **Privacy by construction, not by promise.** A fail-closed gate keeps birth data, chart language, and rationale local. Only de-identified visual tokens leave — behind a field whitelist, a chart-language scan, and a SHA-256 lock on every artifact.
- **Two-skill boundary.** `hatch-pet` owns the body (canonical base, animation rows, final package); this skill owns the translation (chart → candidate → Character Bible) and the delivery gate (selection lock, visual-QA record, atomic install). It renders *from* an official base, never redefining the character — identity is authored once and hash-locked.

## How it works

```text
your birth (private)
  → local chart computation          # PyJHora + Swiss Ephemeris; credential-free, never leaves
  → three visual-safe candidates      # LLM-authored from de-identified facts; gated
  → three official Hatch bases        # canonical identity, owned by hatch-pet
  → three Character Bibles            # text-bearing boards; render FROM the base, never redefine it
  → you choose one
  → nine-state animation, QA, an installable Codex pet
```

The official **hatch-pet** skill owns the body; **Vedic Companion IP** owns the translation. The figure is made once, hash-locked, and kept identical across every later stage.

## Quick start

Install the skill:

```bash
git clone https://github.com/hazelian0619/vedic-companion-ip.git
cd vedic-companion-ip
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/skill" "$HOME/.codex/skills/vedic-companion-ip"
```

Check your environment — it will offer to install what is missing:

```bash
python3 "$HOME/.codex/skills/vedic-companion-ip/scripts/preflight.py"
```

Set your image provider in your own process environment — never commit it:

```bash
export IMAGEV2_API_KEY='sk-...'        # yours; never written anywhere
export IMAGEV2_ENDPOINT='https://tok.fan/v1'
export IMAGEN_MODEL='gpt-image-2'
```

Then, in Codex:

```text
From my birth information, make three long-term companion directions. Compute
locally, show me the three design boards, and make the pet only after I choose.
```

The full operational manual — every command, the input contract, the failure rules — is [skill/SKILL.md](skill/SKILL.md).

## The privacy gate

What you give — date, time, place, coordinates, timezone — stays where you gave it. It does not enter a prompt, a manifest, the repository, or the package. The chart report and the reasoning stay private; only de-identified visual tokens are allowed outward, and only behind a gate that fails closed.

| kept private, never leaves | allowed outward, image-safe |
| --- | --- |
| birth date, time, place, coordinates, timezone | three design-safe candidates |
| the raw chart report and reasoning | the Hatch canonical base |
| the candidate evidence ledger | the Character Bible, selection, QA, animation |

The gate is not a setting. It is a mechanism:

- **Field whitelist** — only the Character Bible contract schema is accepted. Any unrecognized field stops the flow.
- **Chart-language scan** — English and East-Asian scripts are scanned for planet / sign / house / nakshatra / dignity / dasha / atmakaraka terms. A hit stops the flow.
- **SHA-256 per artifact** — every accepted base, board, and selection is hash-locked. Drift is detected, not re-derived.
- **Fail-closed state machine** — the session advances `chart_ready → candidates_ready → selection → hatch` only through bundled commands. No stage can be skipped; any gate failure stops before any external call.
- **Process-only credentials** — API keys live in your shell environment, never in a file, a prompt, a manifest, or an image.

Eleven adversarially-verified gate bypasses have been closed and are covered by the test suite.

## The Character Bible — one board per candidate

A Character Bible is one image board per candidate. It carries three kinds of evidence — behavior, structure, and what must not change — laid out as a specimen dossier (Swiss information design for hierarchy, industrial-design review for structural proof, collection documentation for the captions).

- **Behavior** — a small `before → response → resolve` sequence: a situation arrives, the companion answers it, the matter settles.
- **Structure** — layered, matte materials; a palette derived from this chart's own color character (never a default); one authored signature carried everywhere.
- **What must not change** — the canonical identity. A drifted board is regenerated from the official base; the base is never changed to fit the board.

## What the system will not do

- It will not send your birth data, your chart, or its reasoning to image generation.
- It will not pick the companion for you. It stops at three until you choose.
- It will not re-derive the chosen character. The base and board are locked; a drifted frame is repaired from the canonical base, never redrawn from scratch.
- It will not proceed past a failed gate. A privacy failure stops the flow before any external call.

## Development

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q        # 135 tests; CI runs on every push
```

The repository ships only the workflow and its quality gates. No real user's pet, chart, image, or key is ever committed.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Composed of official and local parts: **hatch-pet** (canonical bases, animation, packaging), **imagegen** (the image CLI), **vedic-calculator** (the local chart runtime), and **PyJHora** / **pysweph** ([Swiss Ephemeris](https://www.astro.com/swisseph/)) for the astronomy and the classical Jyotish computations.
