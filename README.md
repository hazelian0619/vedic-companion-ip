# Vedic Companion IP

An installable Codex Skill that turns a user's private birth input into three
design-safe companion-pet candidates. It computes chart facts locally, keeps
all private evidence out of image requests, uses official `hatch-pet` to own
the canonical pet and animation, then uses image generation only for the
text-bearing Character Bible.

## Workflow

```text
private intake -> local chart computation -> three safe candidates
-> three official Hatch bases -> three Character Bibles -> user selection
-> selected Hatch animation -> QA -> Codex pet package
```

The full operational contract is in [skill/SKILL.md](skill/SKILL.md).

## Install Locally

```bash
git clone https://github.com/hazelian0619/vedic-companion-ip.git
ln -s "$(pwd)/vedic-companion-ip/skill" "$HOME/.codex/skills/vedic-companion-ip"
```

The Skill requires the local `hatch-pet` and `imagegen` Skills. Image-provider
credentials are process environment variables only; never write them to this
repository, a session manifest, or a prompt.

## Development

```bash
python3 -m pip install -r requirements.txt
PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider
python3 "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" skill
```

## Privacy Boundary

This repository intentionally excludes private intake, dates, locations,
coordinates, chart reports, candidate rationale, generated sessions, and
artwork. The source code includes local-only types and privacy gates needed to
process those values safely, but no real user data or credentials.
