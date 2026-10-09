# Design system — "control room"

Reference comps: `docs/design/comps/`. Values below are extracted from them and are normative.

## 1. Typography
- UI: **IBM Plex Sans** 400/500/600. Numbers, ids, units, code: **IBM Plex Mono** 400/500.
  Section labels: **IBM Plex Sans Condensed** 500/600, uppercase, letter-spacing .04–.05em.
- Self-host fonts (`@fontsource/ibm-plex-*`) — static mode must work offline.
- Scale (px): 11 label · 12 meta · 13 dense table · 14 body · 15–17 card title · 20 well id · 26–28 page title.
- All numbers `font-variant-numeric: tabular-nums`.

## 2. Colour tokens (CSS variables in `styles/tokens.css`)
| Token | Dark (default) | Light |
|---|---|---|
| `--bg` | #0A0E13 | #F5F7FA |
| `--bg-nav` | #0D1218 | #FFFFFF |
| `--panel` | #11171E | #FFFFFF |
| `--panel-2` | #161D25 | #EEF2F6 |
| `--line` | #243040 | #D5DCE4 |
| `--line-soft` | #1B2430 | #E6EBF0 |
| `--text` | #DCE3EA | #121820 |
| `--text-2` | #A9B6C3 | #3D4A58 |
| `--text-3` | #93A1B0 | #5A6878 |
| `--accent` (brand amber) | #F5A524 | #B86E00 |
| `--link` | #7CC4FF | #0B62B0 |
| `--danger` | #FF6B6B | #C62828 |
| `--ok` | #3DDC97 | #1E7F55 |
| `--mock-bg` / `--mock-fg` | #2A2112 / #F5C46B | #FFF3D6 / #7A4B00 |
Body text ≥ 4.5:1 on its background in both themes; check with the a11y test (T10.3).

## 3. Rig-state palette (colour + pattern + label — never colour alone)
| State | Fill (dark) | Pattern | Label text |
|---|---|---|---|
| rotary_drilling | #1F64AA | solid | #FFFFFF |
| sliding | #9CCBF5/#6FA6D8 | 135° stripes 4 px | #0A0E13 |
| connection | #E39A1E | solid | #0A0E13 |
| trip_in | #B58CFF/#9670E0 | vertical stripes 4 px | #0A0E13 |
| trip_out | #5B3FA8 | solid | #FFFFFF |
| reaming | #4FD1AE/#2A9C7E | vertical stripes 3 px | #0A0E13 |
| circulating | #5E7387 | solid | #FFFFFF |
| out_of_hole | #2A3440 | solid | #DCE3EA |
| unknown / gap | #3A4552 on #161D25 | 45° hatch 2/7 px | #C8D2DC |
In canvas (uPlot) render patterns with `CanvasPattern` built once per theme. Labels drawn when the interval
is ≥ 56 px wide. A legend is always visible under the ribbon.

## 4. Confidence badge
| Level | Glyph | Dark bg/fg | Text |
|---|---|---|---|
| high | ▲ | #123826 / #6FF0B4 | "High" |
| medium | ◆ | #3A2C10 / #FFC861 | "Medium" |
| low | ▼ | #3A1515 / #FF9A9A | "Low" |
| insufficient | ○ | #161D25 / #A9B6C3 | "Insufficient data" |
Reason always available on hover/focus (tooltip) and in the copilot card text.

## 5. Coverage cell
full ● on #2E7D5B · partial ◐ on amber 45° stripes · none ○ on --panel-2 with border. 52×26 px.

## 6. Core components (props are normative)
- `<Num q={Quantity} kind?="inline|kpi" showUnit?>` — formats with precision, converts units via prefs,
  dashed underline in --link; hover/focus opens `<EvidencePopover id>`; `verified === false` → red solid
  underline on red-tinted bg + "✕ not verified" in popover; missing evidence → dev-only console.error.
- `<EvidencePopover id>` — tool, params (mono), sources (file, sha256 short, channels, window), value SI +
  converted, link "Show this window in the workspace".
- `<ConfidenceBadge c={Confidence}>` · `<MockBadge/>` (dashed amber border) · `<ModeBadge/>` ("STATIC MODE" /
  "LIVE") · `<InsufficientData reason/>` · `<Limitation title text/>`.
- `<Chip>` buttons: min-height 36 px (44 px for primary inputs), 4 px radius, 1 px --line border.
- Card: --panel, 1 px --line, radius 6, padding 16–22.
- Tables: header condensed uppercase 11.5 px --text-3; rows 1 px --line-soft; wide tables in `overflow-x:auto`.
- Nav: 56 px, brand "STRATA" condensed amber letter-spacing .14em; links Field · Workspace · Performance ·
  Formation · Trust; right side: ModeBadge, units toggle, Copilot toggle.

## 7. Layout
- Pages are fluid: max-width 1360 px for document-like pages (S1, S3, S5); S2/S6 use full width with the
  copilot dock (flex: 1 1 400px) on the right; at < 1100 px the dock becomes a bottom sheet.
- Track gutter (label column) fixed 148 px on S2 so every track aligns.
- Phone width: nav wraps, tables scroll, dock becomes full-screen sheet. No horizontal page scroll.

## 8. Accessibility
Real `<button>`/`<a>`/`<input>` with labels; icon-only buttons have `aria-label`; focus rings visible
(2 px --link); charts expose a text alternative (current window summary + "download CSV of visible data");
keyboard: ←/→ moves cursor by 1 bucket, +/- zoom, Esc closes popovers. No global keydown handlers outside
the chart that has focus.

## 9. Copy lint {#copy-lint}
Forbidden in UI strings (CI grep, case-insensitive): `autopilot`, `optimal setpoint`, `recommended WOB`,
`recommended RPM`, `guaranteed`, `% NPT reduction`, `fleet-wide`, `AI-powered` (as a claim), any vendor product
name. "Best parameter window" must always be accompanied by the word "advisory".
Required phrases: data gaps "no data · N min"; empty states say what is missing and why.
