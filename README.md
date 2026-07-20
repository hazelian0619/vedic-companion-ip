# Vedic Companion IP

> Turn locally-computed birth-chart facts into a long-term Codex companion pet —
> without sending birth data, chart language, or rationale to image generation.

[![CI](https://github.com/hazelian0619/vedic-companion-ip/actions/workflows/ci.yml/badge.svg)](https://github.com/hazelian0619/vedic-companion-ip/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](requirements.txt)

Vedic Companion IP is an installable Codex Skill that builds a personalized
companion pet from a Vedic (Jyotish) birth chart. It is **not** a one-shot image
generator. It computes the chart locally, converges it into three design-safe
candidate characters, lets you pick one, then hands the selected identity to the
official `hatch-pet` skill for stable nine-state animation and packaging.

The product's core constraint is **privacy by design**: raw birth data, chart
reports, and reasoning never leave your machine and never enter an image prompt.
Only de-identified visual tokens reach the image model, behind a hard,
code-enforced gate.

## Table of contents

- [How it works](#how-it-works)
- [Privacy by design](#privacy-by-design)
- [Quick start](#quick-start)
- [What you get](#what-you-get)
- [Development](#development)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## How it works

```text
private intake
  -> local chart computation            (PyJHora + Swiss Ephemeris, local only)
  -> three visual-safe IP candidates   (LLM-authored, gated)
  -> three official Hatch canonical bases
  -> three text-bearing Character Bibles
  -> user chooses one
  -> selected Hatch animation, QA, and Codex pet package
```

Two skills own two responsibilities:

- The official **`hatch-pet`** skill owns the canonical character base, the
  nine-state animation, and the final install package.
- **Vedic Companion IP** owns the chart→candidate translation and the
  text-bearing Character Bible. It renders *from* an official base; it never
  redefines the character.

This separation is why the companion stays visually stable across animation
frames instead of being re-guessed on every generation.

## Privacy by design

| Local private layer (never leaves) | Public layer (image-safe) |
| --- | --- |
| Birth date, time, place, coordinates, timezone | Three design-safe candidate characters |
| Raw chart report and rationale | Hatch canonical base |
| Private candidate evidence ledger | Character Bible, selection record, QA, animation package |

The private layer never enters an image prompt, a Skill artifact, the Git
repository, or the install package. The public layer is checked by schema
whitelist, keyword + East-Asian-script scanning, SHA-256 locking, and session
state gates. Credentials are process-only environment variables — never written
to files, source, prompts, or images.

## Quick start

### 1. Install the skill

```bash
git clone https://github.com/hazelian0619/vedic-companion-ip.git
cd vedic-companion-ip
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/skill" "$HOME/.codex/skills/vedic-companion-ip"
```

The link does not overwrite an existing skill of the same name; to update, remove
the old link first, then recreate it.

### 2. Verify your environment (preflight)

```bash
python3 "$HOME/.codex/skills/vedic-companion-ip/scripts/preflight.py"
```

`preflight` detects the local Vedic runtime, the official `hatch-pet` skill, the
`imagegen` system skill, and your image-API credentials. With `--auto-install`
(the default) it installs the Vedic runtime into a scoped venv and clones
`hatch-pet` when `HATCH_PET_REPO` is set; it verifies the image API with a live
`/v1/models` call. `--check` is read-only (for CI). Any missing dependency exits
non-zero (fail-closed) and stops the flow before any external call.

### 3. Set your image API (process env only, never commit)

```bash
export IMAGEV2_API_KEY='sk-...'               # your key; never commit it
export IMAGEV2_ENDPOINT='https://tok.fan/v1'
export IMAGEN_MODEL='gpt-image-2'
```

### 4. Use it in Codex

```text
From my birth information, make three selectable long-term companion-pet
directions; compute locally, show me the character design boards first, and
make the Codex pet only after I select one.
```

The full runtime commands, input contract, and failure rules are in
[skill/SKILL.md](skill/SKILL.md) — the single operational manual for automated
execution.

## What you get

1. **Local-only computation.** You provide birth info locally; the system
   computes but never sends raw input, coordinates, the report, or reasoning to
   the image service.
2. **Three directions, not one.** You see three genuinely distinct companion
   directions — authored from your chart's actual tensions, not a fixed
   taxonomy — instead of a single algorithm-decided answer.
3. **A human decision preserved.** You pick one of the three. The system never
   picks the final companion for you.
4. **Stable identity across animation.** Your selection locks the canonical base
   and board by SHA-256, so the subsequent nine-state animation cannot silently
   switch to a different character. Every layer protects one identity instead of
   re-guessing what it should look like.

Each stage is an auditable session state with fail-closed rules: no base → no
Bible; identity drift → regenerate the board, never the base; no selection →
stop at three boards; any privacy-gate failure → stop before any external call.

## Development

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q                 # 135 tests; CI runs on every push/PR
```

The repository ships only executable production source, the Skill, tests, and
docs. All real user data, session artifacts, images, reports, private evidence,
and credentials are Git-ignored and cannot be committed.

## License

MIT — see [LICENSE](LICENSE). The repository ships the reusable workflow and
quality gates; it does not ship any real user's pet, chart, image, or service key.

## Acknowledgments

This skill composes external skills and a local astronomy stack:

- **hatch-pet** (official Codex skill) — owns every canonical character base,
  animation row, and the final install package.
- **imagegen** (system skill) — the official image CLI used for base + board jobs.
- **vedic-calculator** — the local runtime for deterministic chart computation.
- **PyJHora** and **pysweph / [Swiss Ephemeris](https://www.astro.com/swisseph/)**
  for ashtakavarga, dasha, shadbala, and divisional charts.
