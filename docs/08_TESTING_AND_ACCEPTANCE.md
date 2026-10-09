# Testing and acceptance

## 1. Test pyramid
| Layer | Tool | What |
|---|---|---|
| Contracts | pytest + jsonschema; vitest + zod | every fixture/export file validates; evidence ids resolve; sums hold |
| Pipeline | pytest | QC, rig-state rules, KPIs, ILT, reconciliation, confidence on scripted synthetic data with known answers; determinism of `make reproduce` |
| API | pytest + httpx | every route validates against schema; SSE event order; verifier cases |
| Web units | vitest + Testing Library | units, formatters, stores/URL sync, series decoder, level chooser, trust kit |
| Visual | Playwright screenshots | fixed windows of S1, S2, S3, S5, S6 in both themes (update only intentionally) |
| E2E | Playwright | demo script (below) in static mode |
| A11y | @axe-core/playwright | every route, both themes |

## 2. Synthetic test oracle
`pipeline/strata_pipeline/fixtures/synth.py` generates sensor data from a scripted sequence of rig states with
known durations. Tests assert the classifier recovers states (≥ 98 % of seconds outside ±5 s boundaries) and
KPIs/ILT equal the scripted values exactly.

## 3. Demo-script e2e (`apps/web/e2e/demo.spec.ts`) — P0 acceptance
Run against `vite build && vite preview`, no `VITE_API_URL`, `?fast=1`.
1. `/field`: ≥ 9 rows; coverage cells have glyphs; at least one Low badge; MOCK badge present (fixtures).
2. Click the rich Volve well → `/well/…/workspace`; press "Fit connection"; assert ribbon shows a
   `connection` interval under the cursor and the DDR lane bar is present at the same x (±2 px); click a
   mismatch ▲ → popover contains "Sensors say" and "Report says".
3. Nav to Performance: waterfall total text equals sum of category values; click an outlier → URL is a workspace
   deep link with `t0/t1` and the cursor window contains the outlier interval.
4. Open copilot, click suggestion "What drove the lost time in the 12¼″ section?" → AnswerCard visible with
   ≥ 3 claims; click first claim → popover shows `tool` and a source file; open tool trace → ≥ 3 steps.
5. Nav to Trust: ablation table header shows gold-set status; limitations list has ≥ 5 items.
6. (P1 flag) Replay 60× for 5 s → ≥ 1 alert toast.
Plus: reload any step's URL → same view (deep-link check).

## 4. Performance budgets (S2, 30-day fixture, 7 channels, mid laptop, Chromium)
First meaningful render ≤ 1.5 s after data cached · pan/zoom ≥ 50 fps median over 3 s of scripted wheel input ·
JS bundle ≤ 450 kB gzip for initial route (lazy-load ECharts and S6+) · static export per well ≤ 25 MB.

## 5. Definition of done — P0
All of §3 green from a fresh clone (`git clone && make setup && make e2e`), no API key, CI green, a11y clean,
copy-lint clean, Sergei's visual review against comps passed.
