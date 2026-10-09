# Design comps

Source canvas (Claude Design artifact, private to Sergei): https://claude.ai/code/artifact/73c42139-5374-4738-af58-5bd7a947764f

Files in `comps/` are exported artboards in the `.dc.html` format (HTML + a small template language):
`{{name}}` holes and `<sc-for list=… as=…>` loops are filled by the `renderVals()` function in the
`<script type="text/x-dc">` block at the bottom of each file. They do not render standalone in a browser
(they need the canvas runtime), so read them as **layout + style specs**:
- inline `style="…"` values are the exact spacing, sizes and colours (tokens in `docs/05_DESIGN_SYSTEM.md`);
- `renderVals()` shows the mock data shape and how series/paths were generated (useful for the fixture
  synthesizer, T1.2);
- all numbers in comps are illustrative mock values; bracketed `[…]` items are placeholders for real data.

| Comp | Screen | Spec |
|---|---|---|
| `Main.dc.html` | Plan & spec v0.2 (sections 1–11) | `docs/01_PRODUCT_SPEC.md`, `docs/02_IMPLEMENTATION_PLAN.md` |
| `S1-Field.dc.html` | S1 Field overview | `06_SCREENS.md#s1` |
| `S2-Workspace.dc.html` | S2 Workspace + S4 Copilot dock | `06_SCREENS.md#s2`, `#s4` |
| `S3-Performance.dc.html` | S3 Performance (+ PR-1, PR-2 panels) | `06_SCREENS.md#s3` |
| `S5-Trust.dc.html` | S5 Trust (+ v0.2 panels) | `06_SCREENS.md#s5` |
| `S6-Formation.dc.html` | S6 Formation (P1, PR-3, PR-4) | `06_SCREENS.md#s6` |
## Rendered exports (`rendered/`)
Self-contained HTML exports of artboards (runtime and fonts bundled) — open directly in a browser to see the
exact look. These are the **pixel reference** for visual review; the `.dc.html` comps are the **markup
reference** (exact styles, mock-data shapes).
| File | Screen | Status |
|---|---|---|
| `rendered/S1-Field.html` | S1 Field overview | exported |
| `rendered/S2-Workspace.html` | S2 Workspace + S4 Copilot | not yet exported |
| `rendered/S3-Performance.html` | S3 Performance | not yet exported |
| `rendered/S5-Trust.html` | S5 Trust | not yet exported |
| `rendered/S6-Formation.html` | S6 Formation | not yet exported |
Notes: nav links inside a single-artboard export do not navigate (other screens are separate files).
Do not import, copy or bundle these files into `apps/web` — rebuild the UI with the real stack.

Screens without comps (S7, S8, S9–S11) are specified in `06_SCREENS.md`; reuse the patterns above.
When a comp and a spec disagree, the spec wins; note the difference in the task summary.
