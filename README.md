# Vedic Companion IP

> Your birth moment, read in private, becomes a small companion that lives on
> your desktop — and stays.

[![CI](https://github.com/hazelian0619/vedic-companion-ip/actions/workflows/ci.yml/badge.svg)](https://github.com/hazelian0619/vedic-companion-ip/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

You give a date, a time, a place — the moment you arrived in the world. The
skill reads it locally and sets the chart aside; it never travels onward. What
returns is not one answer but three: three small beings, each a different shape
of staying close. One might be a pocket shelter; another a guiding lantern;
another a clasped connector. They arrive on boards laid out like museum
specimens, and the choice is left to you.

The one you keep is made to stay. Silhouette, palette, and gait are locked
across nine states — idle, running, waiting, rest — so it is the same being
from the first frame to the last, never re-guessed, never redrawn from
scratch. The chart stays your secret; the companion stays your own.

This is not a one-shot image. It is one being, made carefully, born of your
stars without repeating them.

## How it works

```text
your birth (private)
  -> local chart computation          # PyJHora + Swiss Ephemeris; never leaves
  -> three candidate companions       # the reading, authored into form; gated
  -> three official Hatch bases
  -> three text-bearing Character Bibles
  -> you choose one
  -> nine-state animation, QA, an installable Codex pet
```

Two skills, two responsibilities — kept separate on purpose:

- The official **hatch-pet** skill owns the body: the canonical base, the
  animation rows, the final package.
- **Vedic Companion IP** owns the translation — the reading of the chart into
  a candidate, and the text-bearing Character Bible. It renders *from* an
  official base; it never redefines the character.

The boundary exists so the companion cannot drift: the figure is made once,
documented, and held to itself.

## The secret, and the gate

What you give — date, time, place, coordinates — stays where you gave it. It
does not enter a prompt, a manifest, the repository, or the package. The chart
report and the reasoning stay private; only de-identified visual tokens are
allowed outward, and only behind a gate that fails closed.

| kept private, never leaves | allowed outward, image-safe |
| --- | --- |
| birth date, time, place, coordinates, timezone | three design-safe candidates |
| the raw chart report and reasoning | the Hatch canonical base |
| the candidate evidence ledger | the Character Bible, selection, QA, animation |

The gate is not a setting. It is a whitelist of fields, a scan for chart
language (English and East-Asian scripts), a SHA-256 lock on every accepted
artifact, and a state machine that refuses to skip a stage. Credentials live
only in your process environment — never in a file, a prompt, or an image.

## A Character Bible, not a card

Each candidate comes with a Character Bible: one board, laid out like a museum
specimen dossier — Swiss information design for hierarchy, industrial design
review for structural proof, collection documentation for the short captions.
It carries three kinds of evidence: behavior, structure, and what must not
change.

The behavioral proof is a small sequence — **before, response, resolve** — a
situation arrives, the companion answers it, the matter settles. Not a pose;
a rite. The materials are layered and matte; the palette is drawn from this
chart's own color character; the figure is compact, endearing, and quietly
playful, with one
authored signature it carries everywhere.

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

The full operational manual — every command, the input contract, the failure
rules — is [skill/SKILL.md](skill/SKILL.md).

## What the system will not do

- It will not send your birth data, your chart, or its reasoning to image
  generation.
- It will not pick the companion for you. It stops at three until you choose.
- It will not re-guess the chosen character. The base and board are locked; a
  drifted frame is repaired from the canonical base, never redrawn from scratch.
- It will not proceed past a failed gate. A privacy failure stops the flow
  before any external call.

## Development

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q        # 135 tests; CI runs on every push
```

The repository ships only the workflow and its quality gates. No real user's
pet, chart, image, or key is ever committed.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Composed of official and local parts: **hatch-pet** (canonical bases, animation,
packaging), **imagegen** (the image CLI), **vedic-calculator** (the local chart
runtime), and **PyJHora** / **pysweph** ([Swiss Ephemeris](https://www.astro.com/swisseph/))
for the astronomy and the classical Jyotish computations.
