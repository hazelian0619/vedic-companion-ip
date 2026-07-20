# Vedic Companion IP

> Turn birth information computed only locally into a Codex pet that can keep
> the user company long-term. It does not send the chart report to the model,
> nor does it generate a pet from a single generic prompt.

Vedic Companion IP is an installable Codex Skill. It first performs deterministic
chart computation locally, then converges the result into three visual-safe
candidate IPs that carry no personal data. After the user selects one direction,
the official `hatch-pet` skill turns it into an installable, animated Codex pet.

```text
private intake
  -> local chart computation
  -> three visual-safe IP candidates
  -> three official Hatch canonical bases
  -> three text-bearing Character Bibles
  -> user chooses one
  -> selected Hatch animation, QA, and Codex pet package
```

## What the user experiences

1. The user provides birth information only locally. The system computes but does
   not send raw input, coordinates, the report, or reasoning to the image service.
2. The user sees three directions, not a single "only answer" decided for them.
3. Each direction has a Character Bible built from the same Hatch canonical base,
   used to understand the character's silhouette, materials, motion, and the
   recognition features that must not change.
4. Once the user confirms one, only that one proceeds to nine-state animation,
   atlas, visual QA, and the install package.

This order is the product constraint: `hatch-pet` owns the character identity,
animation, and final package; image generation only produces a text-bearing
Character Bible for the same character and cannot redefine the pet.

The whole process lives in one local session. It is not a cloud account or a
black-box queue: the session writes every publicly inspectable stage as
verifiable state and keeps private computation in an owner-only directory. So
the user can pause to think at the three design boards, or continue after
selecting. Any attempt to skip the Hatch base, swap already-selected material,
or feed an external image back into the flow is rejected.

## Two boundaries

| Local private layer | Public layer usable for visual production |
| --- | --- |
| Birth date, time, place, coordinates, timezone | Three design-safe candidate characters |
| Raw chart report and reasoning | Hatch canonical base |
| Private evidence ledger for candidates | Character Bible, selection record, QA, animation package |

The private layer never enters an image prompt, a Skill artifact, the Git
repository, or the install package. The public layer is checked by schema,
keyword scanning, SHA-256 locking, and state gates.

## Install to Codex

Prerequisites: a local Codex, the official `hatch-pet` Skill, the system
`imagegen` Skill, and a working local Vedic runtime. Image-service credentials
stay only in the current process environment.

```bash
git clone https://github.com/hazelian0619/vedic-companion-ip.git
cd vedic-companion-ip
mkdir -p "$HOME/.codex/skills"
ln -s "$PWD/skill" "$HOME/.codex/skills/vedic-companion-ip"
```

The link intentionally does not overwrite an installed Skill of the same name; to
update, inspect and remove the old link first, then recreate it.

After install, describe the need directly in Codex, for example:

```text
From my birth information, make three selectable long-term companion-pet
directions; compute locally, show me the character design boards first, and
make the Codex pet only after I select one.
```

The full runtime commands, input contract, and failure handling live in
[skill/SKILL.md](skill/SKILL.md). That file is the single operational manual for
automated execution.

## Onboarding (preflight)

Before the first run, check the environment and auto-install anything missing:

```bash
python3 "$HOME/.codex/skills/vedic-companion-ip/scripts/preflight.py"
```

preflight detects VEDIC_PY, the official `hatch-pet` skill, the `imagegen`
system skill, and the image-API credentials in your environment. With
`--auto-install` (the default) it installs VEDIC_PY into a scoped skill-local
venv and clones `hatch-pet` when `HATCH_PET_REPO` is set; it verifies the image
API with a live `/v1/models` call. Credentials are read from process env only
and are never printed or written. `--check` is a read-only mode for CI. Set your
image API in your own process environment:

```bash
export IMAGEV2_API_KEY='sk-...'               # your key; never commit it
export IMAGEV2_ENDPOINT='https://tok.fan/v1'
export IMAGEN_MODEL='gpt-image-2'
```

## The rhythm of one full experience

First compute locally and get three candidate directions. The system prepares an
official Hatch run for each direction to form an animatable character base; only
then does it generate a Character Bible with text, material, proportion, and
motion notes from that same base. The user makes a single choice among the three
boards. The selection locks the matching base and board, so the subsequent
nine-state animation cannot silently switch to a different character.

This is why it suits long-term companionship better than "generate one pet image":
every layer protects the same character identity instead of re-guessing what it
should look like on each generation.

## Why not one-shot image generation

Once a character enters animation, the priority is stability, not a single
frame's momentary appeal. So each step has a clear responsibility boundary:

- **Candidate drafter** (`author_candidates.py`): calls an LLM to draft exactly
  three visual-safe directions from de-identified chart facts, guided by the
  authoring framework. It does not compress every user into one palette,
  material, mascot species, or decorative motif.
- **Candidate validator** (`candidate_validator.py`): the hard gate. Enforces the
  schema whitelist, privacy scan, and astrology-term scan fail-closed; requires
  three genuinely distinct directions; records the public candidates and the
  private evidence ledger.
- **Hatch base**: establishes a unique, animatable character identity for each
  direction.
- **Base acceptance**: registers only the three session-owned canonical bases
  whose base job completed and passed visual review; this is the explicit
  handoff from Hatch base to Character Bible.
- **Character Bible**: uses the same base to present identity, proportion,
  material, and behavior notes in a professional layout. The v3 layout draws on
  Swiss information design, industrial design review, and museum collection
  documentation; it uses `before -> response -> resolve` as character behavior
  evidence, not a set of replaceable static cards. It does not fix the product
  palette, material, or typeface.
- **Character Bible QA**: confirms identity consistency, readable text, and
  complete layout before a candidate becomes selectable.
- **Selected Hatch run**: locks the hash of the selected base and board and
  rejects old branches or tampered material.
- **Delivery QA**: the nine-state previews, frame checks, atlas validation, and
  explicit visual acceptance must all pass.

## Development and verification

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skill
```

The repository keeps only executable production source, the Skill, tests, and
documentation. All real user data, session artifacts, historical images,
reports, private evidence, and credentials are Git-ignored and cannot be
committed.

## Current boundaries

This repository ships the reusable workflow and quality gates. It does not ship
any real user's pet, chart, image, or service key. The user's selection of a
character is an intentional human decision; the system never picks the final
companion from the three directions on the user's behalf.
