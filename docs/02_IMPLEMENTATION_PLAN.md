# STRATA — Implementation plan (ICA: instructions for the coding agent)

Goal: a product that looks like the comps in `docs/design/comps/` and behaves as `01_PRODUCT_SPEC.md` v0.2
describes, delivered as phases with explicit tasks, files, steps and acceptance criteria.

## How to use this plan
- Execute tasks **in the order of §2** (the critical path). Tasks in the same "lane" can be interleaved.
- Each task lists: **Goal · Depends · Files · Steps · Accept**. A task is done only when *Accept* passes and
  `CLAUDE.md §6` holds. Tick it in `tasks/BACKLOG.md`.
- Front end is built against **fixtures in final shapes** first (Lane A); the real data pipeline (Lane B)
  replaces fixtures later without UI changes. Do not block Lane A on Lane B.
- Keep each change set to one task. If a task exceeds ~600 changed lines, split it into `Tx.ya/b` and note it.

## 1. Milestones
| Milestone | Contains | Exit criterion |
|---|---|---|
| **M0 Foundations** | Phase 0, 1, 4 | `make web` shows the shell with S1 on fixtures; contracts generated; CI green |
| **M1 Workspace** | Phase 5, 6 | Demo beats 1–2 pass on fixtures |
| **M2 Performance & Copilot (static)** | Phase 7, 8a | Demo beats 3–4 pass on fixtures with recorded sessions |
| **M3 Trust + P0 e2e** | Phase 9, 10 | Playwright demo-script test green in static mode from fresh clone |
| **M4 Real data** | Phase 2, 3, 8b | Fixtures replaced by Volve/FORGE exports; MOCK badges gone; e2e still green |
| **M5 P1** | Phase 11–13 | S6, S7, replay; PR-3/PR-4 model cards with real metrics |
| **M6 P2** | Phase 14 | S9–S11 |

## 2. Critical path order
T0.1 → T0.2 → T0.3 → T1.1 → T1.2 → T1.3 → T4.1 → T4.2 → T4.3 → T4.4 → T5.1 → T6.1 → T6.2 → T6.3 → T6.4 →
T6.5 → T7.1 → T7.2 → T8.1 → T8.2 → T9.1 → T10.1 → T10.2 → T10.3 → **[M3]** → T2.1 → T2.2 → T2.3 → T2.4 →
T3.1 → T3.2 → T3.3 → T3.4 → T3.5 → T3.6 → T3.7 → T8.3 → T8.4 → T8.5 → T9.2 → T10.4 → **[M4]** → T11.x → T12.x
→ T13.x → **[M5]** → T14.x.

---
## Phase 0 — Repository and tooling (Lane A+B)

### T0.1 Monorepo scaffold
Goal: runnable empty monorepo. Depends: —.
Files: `Makefile`, `.gitignore`, `.editorconfig`, `pnpm-workspace.yaml`, `package.json`, `pyproject.toml`
(uv workspace: `pipeline`, `services/api`, `eval`), `apps/web/` (Vite React TS template), `pipeline/`,
`services/api/`, `eval/`, `data/.gitkeep`.
Steps: create Vite app (`react-ts`), enable TS `strict`, `noUncheckedIndexedAccess`; ESLint (typescript-eslint,
react-hooks), Prettier; Python ruff + mypy (strict for `pipeline`); `.gitignore` covers `data/raw`,
`data/interim`, `node_modules`, `.venv`, `apps/web/dist`. Makefile targets from `CLAUDE.md §4` (stubs allowed).
Accept: `make setup && make web` serves a blank page; `make test` runs (0 tests ok); lint passes.

### T0.2 CI
Files: `.github/workflows/ci.yml`. Steps: jobs `web` (pnpm install, lint, typecheck, vitest, build),
`python` (uv sync, ruff, mypy, pytest), `contracts-check`, `copy-lint` (grep list from design system §9),
`e2e` (added in T10.1). Accept: workflow valid (act or push by Sergei later); all jobs green locally via make.

### T0.3 Fonts, Tailwind and tokens
Files: `apps/web/src/styles/tokens.css`, `tailwind.config.ts`, `src/styles/tailwind.css`.
Steps: install `@fontsource/ibm-plex-sans`, `-mono`, `-sans-condensed`; define every token from
`05_DESIGN_SYSTEM.md §2` for `[data-theme=dark]` (default) and `[data-theme=light]`; map Tailwind colours to
`var(--token)`; rig-state and confidence colours as tokens.
Accept: a `/dev/tokens` route (dev only) renders all tokens in both themes; contrast unit test (compute WCAG
ratio for text/bg pairs) passes ≥ 4.5.

---
## Phase 1 — Contracts and fixtures (Lane A)

### T1.1 Code generation
Depends: T0.1. Files: `contracts/codegen/gen_ts.mjs`, `gen_py.sh`, `apps/web/src/contracts/{types,zod}.ts`,
`pipeline/strata_pipeline/contracts.py`.
Steps: generate from `contracts/schemas/strata.schema.json` (`$defs` → named exports); add `make contracts` and
`make contracts-check`.
Accept: generated files compile (tsc, mypy); `contracts-check` fails when schema changes without regen.

### T1.2 Fixture generator
Depends: T1.1. Files: `pipeline/strata_pipeline/fixtures/{generate.py,synth.py}`, output →
`apps/web/public/data/**` (layout in `04_DATA_CONTRACTS.md §3`).
Steps: deterministic (seeded) synthetic data for 3 wells mirroring the comps: `15_9-F-11_A` (rich Volve, 4
sections, 30 days, 1 Hz, one 4-min gap per day, reaming inside DRILL rows, slow connections), `15_9-F-5`
(sparse, missing time logs on some days → low confidence), `16A_78-32` (FORGE, deviated). Plus 6 more
`WellSummary` rows (no detail data) so S1 shows ~9 wells. Synthesize sensor channels from a rig-state script
(as the S2 comp's generator does), DDR rows at 15–30 min granularity with deliberate disagreements, mismatches,
KPIs/ILT computed **by the real KPI code path once it exists; until then by `synth.py` with identical
formulas**, evidence records for every Quantity, 3 recorded copilot sessions (incl. one with an unverified
claim and one `insufficient_data`), eval.json with `gold_set.status = pending`, repro.json. All `is_mock = true`.
Accept: `make fixtures` writes everything; every JSON validates against the schema (pytest); every
`evidence_id` referenced exists; sums (ILT total = Σ categories = Σ sections = Σ days) hold.

### T1.3 Series pyramid writer + reader
Depends: T1.2. Files: `pipeline/strata_pipeline/export/series.py`, `apps/web/src/data/seriesDecoder.ts`.
Steps: implement STRS format and L0–L6 min/max pyramid; TS decoder returning `{t: Float64Array, min, max}`
with NaN → null-mapped arrays for uPlot; level selection function.
Accept: round-trip test (python writes, TS reads in vitest via fixture file) equal within f32; min/max
preserved for injected spikes at every level; level chooser unit-tested.

---
## Phase 4 — Web shell and trust kit (Lane A)

### T4.1 DataSource layer
Depends: T1.1–T1.3. Files: `src/data/{DataSource.ts,StaticSource.ts,HttpSource.ts,createDataSource.ts,
hooks.ts,evidenceIndex.ts,sessionPlayer.ts}`.
Steps: implement interface from `03_ARCHITECTURE.md §3.1`; zod-validate in dev/test; TanStack Query hooks
(`useWells`, `useSections`, `useSeriesWindow(well, channels, t0, t1, px)` which picks level, fetches chunks,
concatenates, caches by chunk key); evidence lookup via shard map; session player honours `dt_ms` (cap 1.5 s;
`?fast=1` → 0 delay for tests).
Accept: vitest covers each method against fixtures; invalid fixture → readable error path.

### T4.2 Stores, routing, URL sync
Files: `src/state/{view,cursor,prefs,replay}.ts`, `src/app/{router.tsx,Shell.tsx,Nav.tsx}`.
Steps: React Router routes from `03_ARCHITECTURE.md §3.2`; `useView` ↔ URL two-way sync (debounced
`replaceState`, `popstate` restores); prefs persisted with try/catch; nav per comps (Field, Workspace,
Performance, Formation, Trust; ModeBadge; units toggle; Copilot toggle).
Accept: deep link restores well, window, panel, evidence popover; back/forward works; units persist reload.

### T4.3 Units registry
Files: `src/units/{registry.ts,format.ts}`. Steps: conversions from `04_DATA_CONTRACTS.md §1`; `format(q,
system, precision)`; axis label helper. Accept: table-driven tests for every unit both ways.

### T4.4 Trust kit components
Files: `src/trust/{Num,EvidencePopover,ConfidenceBadge,MockBadge,ModeBadge,InsufficientData,Limitation}.tsx`.
Steps: per `05_DESIGN_SYSTEM.md §4–6`; popover via Floating UI, focusable, Esc closes; Num in dev logs error
for missing evidence; Storybook-like `/dev/kit` route showing all states.
Accept: RTL tests: hover/focus opens popover with tool, params, sources, both unit systems; unverified styling;
keyboard access; axe has no violations on `/dev/kit`.

---
## Phase 5 — S1 Field overview

### T5.1 S1 screen
Depends: T4.x. Files: `src/screens/S1Field/*`. Steps: implement `06_SCREENS.md S1` exactly as comp
`S1-Field.dc.html` (filter bar, legend, table with coverage cells, QC bar `<Num>`, badges, explainer cards);
filters in URL; row → workspace deep link with default window (computed from sections + coverage).
Accept: demo beat 1 visually matches comp (side-by-side screenshot review by Sergei); tests for filter logic.

---
## Phase 6 — S2 Well workspace (critical; time-box each task)

### T6.1 TrackStack core
Files: `src/charts/TrackStack/{TrackStack.tsx,useUplot.ts,sync.ts,axes.ts}`. Steps: N uPlot instances, shared
x-scale and `cursor.sync`, fixed 148 px gutter rendered in React (label, unit, cursor readout via
`useCursor`), min/max band series + mid line, null gaps; wheel zoom around cursor, drag pan, limits 2 min…full;
resize observer. Accept: 7 tracks × 30 days at chosen level ≥ 50 fps pan (perf test with `performance.now`
in Playwright, T10.2); cursor line aligned across tracks to ±1 px.

### T6.2 Plugins: gaps, sections, cursor
Files: `src/charts/plugins/{gapHatch,sections,cursorLine}.ts`. Steps: hatched rects from gap intervals with
"no data · N min" label when ≥ 40 px; section shading; Accept: visual test snapshots (Playwright screenshot of
fixed window) stable.

### T6.3 Depth-vs-time chart + overview brush
Files: `src/charts/DepthTime/{DepthTime.tsx,Overview.tsx}`. Steps: inverted y; casing ▼; overview strip
(full well) with draggable/resizable brush bound to `useView.timeRange`. Accept: brush drag updates all tracks;
URL updates; keyboard accessible brush (arrow keys move, shift+arrow resize).

### T6.4 Rig-state ribbon, DDR lane, mismatches
Files: `src/charts/plugins/{ribbon,ddrLane,mismatch}.ts`, `src/screens/S2Workspace/MismatchPopover.tsx`.
Steps: ribbon draws dominant state per pixel column when intervals < 1 px, patterns via CanvasPattern, labels
when ≥ 56 px; legend component; DDR bars with code + truncated narrative; mismatch ▲ hit-testing; popover per
comp (Sensors say | Report says, overlap, tolerance, Zoom to window, Ask copilot why).
Accept: demo beat 2 complete on fixtures.

### T6.5 S2 assembly
Files: `src/screens/S2Workspace/*`. Steps: header (badge, breadcrumb, zoom buttons, Fit connection,
disabled Replay), layout with dock slot, readouts, empty/loading/error states. Accept: matches comp
`S2-Workspace.dc.html`; units toggle re-labels without refetch.

---
## Phase 7 — S3 Performance

### T7.1 KPI cards, distributions, waterfall
Files: `src/screens/S3Performance/*`, `src/charts/echarts/{KpiDist,Waterfall,ByDay}.tsx`. Steps: per S3 spec
and comp; ECharts themed from tokens; outliers/day bars link to S2.
Accept: demo beat 3; sums test in UI; all numbers via `<Num>`.

### T7.2 [v0.2] Booked-vs-measured + ILT definition + Reproduce (PR-1, PR-2)
Files: `S3Performance/{BookedVsMeasured,IltDefinition,ReproducePanel}.tsx`. Steps: stacked bars per DDR code
from `reconciliation(well)`; segment click → S2 at the intervals; definition text from `ilt.definition`;
repro from `repro()`; copy-to-clipboard. Accept: matches comp lower rows; clipboard test.

---
## Phase 8 — Copilot

### T8.1 Dock and AnswerCard (static)
Files: `src/copilot/{CopilotDock,AnswerCard,ClaimRow,DdrQuote,ToolTrace,Suggestions,ContextLine}.tsx`.
Steps: dock on every screen (right panel ≥ 1100 px, bottom sheet below); streaming render from
`sessionPlayer`; kinds answer/insufficient_data/live_mode_required/out_of_scope; claims through `<Num>`
(verified flag); trace drawer; suggestions filtered by screen+well; URL `panel=copilot&s=<session>`.
Accept: demo beat 4 on fixtures; red unverified claim; every claim popover resolves.

### T8.2 Context plumbing
Steps: each screen publishes `CopilotContext` (screen, well, window, depth, section) to the dock; mismatch
"Ask copilot why" and S6 "Generate formation brief" prefill. Accept: context line always correct (tests).

### T8.3 API service (live mode, serves exports)  [Lane B, after M3]
Files: `services/api/strata_api/{main.py,routes/*.py,settings.py}`. Steps: FastAPI routes per
`contracts/endpoints.yaml` reading `data/export`; binary channel endpoint; CORS for dev. Accept: contract tests
— every route response validates against schema; HttpSource e2e smoke with `VITE_API_URL`.

### T8.4 Copilot agent, tools, verifier
Files: `services/api/strata_api/copilot/{tools.py,agent.py,verifier.py,prompts/system.md}`. Steps: tools from
`07 §12`; Anthropic Messages API tool-use loop (model from `STRATA_LLM_MODEL`, key from env, never logged);
`submit_answer` with CopilotAnswer schema; verifier per `03 §4`; SSE stream of CopilotEvents; timeouts,
max 12 tool calls, graceful `error` event. Accept: unit tests with a fake LLM client (scripted tool calls);
verifier tests (match, unit mismatch, rounding, missing evidence, stray numbers in text).

### T8.5 Recorder and session catalogue
Files: `copilot/recorder.py`, `eval/record_sessions.py`. Steps: record the demo questions (incl. "What drove the
lost time in the 12¼″ section?") per well into `data/export/copilot/sessions/` + index. Accept: static mode
replays real recorded sessions; S4 suggestions show them.

---
## Phase 9 — S5 Trust

### T9.1 S5 screen (incl. v0.2 panels)
Files: `src/screens/S5Trust/*`. Steps: QC table with agreement bars, limitations, ablation table with gold-set
header and empty state, reconciliation heatmap (ECharts), model cards (render "—" + reason while null),
positioning tables (industry practice, TADI — TADI text is a placeholder until Sergei supplies the citation),
repro manifest. Accept: demo beat 5; matches comp.

### T9.2 Eval runners  [Lane B]
Files: `eval/{gold/questions.yaml (template only), run_ablation.py, score.py}`. Steps: four configs; write
`eval.json`. Accept: runs end-to-end on a 3-question smoke set with fake LLM; real run only when gold set
status = final (Sergei).

---
## Phase 10 — P0 acceptance

### T10.1 Playwright demo-script test
Files: `apps/web/e2e/demo.spec.ts`. Steps: implement `08_TESTING_AND_ACCEPTANCE.md §3` beats 1–5 against
`vite preview` static build with `?fast=1`. Accept: green in CI.
### T10.2 Performance budget test
Steps: measure S2 first render and pan fps on the 30-day fixture. Accept: budgets in `08 §4`.
### T10.3 Accessibility + copy lint
Steps: axe on every route in both themes; copy-lint grep job. Accept: zero serious/critical violations.
### T10.4 Real-data re-run  [after Lane B]
Steps: replace fixtures with exports for the real wells; update e2e selectors that depend on fixture names via
a `demo.config.json` (well id, section, session id). Accept: e2e green with real data; no MOCK badge.

---
## Phase 2 — Data acquisition and ingestion (Lane B)

### T2.1 Data inventory
Steps: download Volve and FORGE drilling data; write `docs/DATA_INVENTORY.md` (per wellbore: which of the 6
coverage kinds exist, date spans, sampling, mnemonics, units, time zone) and `docs/LICENSES.md`.
Accept: inventory table covers every wellbore; licence text recorded; `data/raw/MANIFEST.json` with sha256.
**Stop and report to Sergei if licence terms restrict redistribution of derived data.**

### T2.2 Volve WITSML/time-log ingest · T2.3 Volve DDR ingest · T2.4 FORGE ingest
Files: `pipeline/strata_pipeline/ingest/*`. Steps: parsers → interim parquet per `07 §2`; mnemonic map; sections
derivation; tops; survey → TVD (minimum curvature). Accept: per-well ingest test on a small sample committed
under `pipeline/tests/samples/` (only if licence allows; else synthetic sample of same structure).

## Phase 3 — Analytics core (Lane B)
T3.1 QC (`07 §3`) · T3.2 rig-state rules (`07 §4`) + gold-sample agreement script · T3.3 KPIs + composite best
(`07 §5`) · T3.4 ILT (`07 §6`) · T3.5 reconciliation + mismatches (`07 §7`) · T3.6 confidence module (`07 §8`)
+ evidence registry · T3.7 exporter (all files of `04 §3`, pyramid, evidence shards, repro manifest, `make
reproduce`). For each: unit tests on synthetic scripted data with known answers (the fixture synthesizer
doubles as the test oracle). Accept T3.7: `make export` produces a schema-valid export; `make reproduce WELL=x`
regenerates byte-identical JSON (deterministic ordering, fixed float formatting).

## Phase 11 — S6 Formation + PR-3 (P1)
T11.1 depth-indexed export (ROP, MSE, dxc, gas, MW, ECD at 1 m) · T11.2 formation classifier + LOWO + card +
predictions (`07 §9`) · T11.3 S6 screen per comp `S6-Formation.dc.html` (depth grid, predicted track with
abstain/disagree patterns, events column, per-formation table) · T11.4 offset compare (flatten on tops) ·
T11.5 depth↔time linking (S6 interval → S2 windows via depthtime) · T11.6 "Generate formation brief" sessions.

## Phase 12 — Events, precursors, S7 (P1)
T12.1 DDR event extraction (rules → optional LLM → review CSV) · T12.2 precursor windows + bands export ·
T12.3 S6 event panel · T12.4 S7 Issue catalogue + summary · T12.5 events model card.

## Phase 13 — Replay (P1)
T13.1 replay event export (alerts per `06 S8`) · T13.2 StaticSource timer replay + WS endpoint · T13.3 S2 replay
controls, toasts, event log; demo beat 6 added to e2e (optional flag).

## Phase 14 — Physics screens (P2)
T14.1 MSE per bit run (S10) · T14.2 torque & drag soft-string model + FF sweep + S9 broomstick (16A) ·
T14.3 surge/swab screening envelope + S11 · T14.4 `full_minus_physics` ablation becomes meaningful.

---
## 3. Risks and mitigations
| Risk | Mitigation |
|---|---|
| S2 performance/complexity | Time-box T6.1 (2 sessions). Fallback: fewer tracks visible by default with "add track" menu. |
| Volve/FORGE structure differs from expectations | T2.1 inventory before any parser; contracts unchanged, only ingest adapts. |
| Rig-state thresholds wrong on real data | Per-well calibration + gold sample; show agreement on S5 honestly. |
| LLM invents numbers | `submit_answer` schema + verifier + red UI; static sessions recorded after verifier passes or kept as the deliberate red example. |
| Licence limits redistribution | Ship code + reproduce command; static export only of permitted derived data. |
| Overclaiming | Copy-lint CI; S5 limitations; "advisory" labels. |
