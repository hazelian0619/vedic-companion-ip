# Candidate Authoring Framework

This is the **standardized thinking** an LLM (or a human author) follows to draft
three companion-pet design directions from a person's de-identified Vedic chart
signals. It is the contract for `scripts/author_candidates.py`'s system prompt.

The standardization lives here and in the candidate schema
([character-bible-contract.md](character-bible-contract.md)) and the privacy
gate — **not** in fixed directions, palettes, or materials. The content is
authored per chart; the boundary is code-enforced.

## 1. What each signal means for a companion

Read these as *design inspiration*, never as literal motifs. Translate each into
companion behavior, form, and material — never into the chart term itself.

| Signal | Design meaning |
|---|---|
| ascendant sign | the companion's **outward stance** — how it presents on first encounter |
| atmakaraka (AK) + its dignity | the **soul's core drive**, and whether it reads as supported (exalted/own sign) or strained (debilitated) |
| dasha lord (mahadasha) | the **current life-rhythm** to echo — the pace and quality of the present chapter |
| moon nakshatra (name only, never pada) | **temperament texture** — the emotional grain of the companion |
| planet dignities | which **energies are available vs strained** — what the companion can do easily vs where it leans |
| house clusters | which **life-arenas are emphasized** for this person — the companion orients toward those |

## 2. How to pick three genuinely distinct directions

**Do NOT use a fixed taxonomy** (no canned shelter/beacon/bridge). Pick three
axes that surface THIS chart's actual tensions.

Examples of tension axes you might derive (choose based on the chart, do not
recite this list):
- settling vs guiding vs connecting
- rest vs momentum vs repair
- sheltering vs beaconing vs bridging
- holding-steady vs reaching-out vs making-room
- quiet-center vs forward-focus vs bilateral-balance

For each of the three, the `form_metaphor` AND the `silhouette_tokens` must be
**genuinely different** from the other two. Three recolorings of one shape is a
failure: the validator rejects a pair that shares `form_metaphor` and
`silhouette_tokens`.

## 3. Each candidate's identity

- **Compact, endearing, tactile.** One authored signature. No literal animals,
  no generic blobs, no scenery, no detached effects.
- The companion is compact and emotionally present — endearing-compact charm
  plus rich tactile material quality (layered, hand-crafted, matte — not cheap
  gloss). Color depth comes from layering, not shine.
- One stable visual signature object the companion carries or shows; it should
  be body-integrated, not a handheld prop.
- `interaction_signature` describes how the companion behaves near the user
  (settles, gathers, bridges, waits, leans in). Make each direction's behavior
  genuinely different.
- `anti_drift` lists what to avoid for THIS direction (no shrine, no armor, no
  toy egg, no wizard costume, etc.) — specific, not generic.

## 4. Privacy rule (non-negotiable, but the validator enforces it anyway)

Candidate text must contain:
- **No astrology terms** — no planet names (Sun, Moon, Saturn, …), no signs
  (Aries, Cancer, …), no nakshatra, dasha, atmakaraka, ascendant, chart,
  horoscope, jyotish, vedic, house, retrograde, rasi, graha. English or Chinese.
- **No birth data** — no dates, times, coordinates, IANA timezones, place names.
- **No rationale or evidence refs** in the candidate itself.

Translate the signal into a visual/behavioral token. "AK = Sun in Leo, own
sign, supported" does NOT become "a sun companion" — it becomes, for example,
"a companion whose core drive is steady warmth, shown as one quiet luminous
center held inside a compact protective form."

## 5. Output contract

Return **only** a JSON object: `{"candidates": [c1, c2, c3]}`. No prose, no code
fences, no fields beyond the schema. Each candidate object has exactly these
fields (see [character-bible-contract.md](character-bible-contract.md)):

```
candidate_id, ip_name, display_name, description, form_metaphor,
silhouette_tokens[], palette_tokens[], material_tokens[],
signature_hook, interaction_signature, board_composition, anti_drift[]
```

- `candidate_id`: a short stable slug, e.g. `settling-<short>-1`.
- `*_tokens` and `anti_drift` are lists of short strings.
- All fields required; the validator rejects unknown fields, missing fields,
  astrology terms, privacy leaks, and non-distinct directions — fail-closed.
