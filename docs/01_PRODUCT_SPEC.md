# STRATA — Product Spec v0.2

v0.1 = original front-end spec. v0.2 adds: decisions on v0.1 gaps (§9), proposals PR-1…PR-6 from the industry
review (§10), new contracts (§11), and the S6 Formation screen design. Changes vs v0.1 are marked **[v0.2]**.

## 1. Purpose and audience
Audience: drilling-digital engineers and product people at Weatherford or AIQ, reviewing a repo link or a
3-minute video. The demo must prove, in order:
1. The system understands rig operations from raw sensor data.
2. It finds lost time that the daily reports don't show.
3. Its AI answers are traceable to evidence, never invented.

Core principle — **trust over polish**: every number is traceable to its source, data gaps are visible,
confidence is explicit, limitations are stated in the app itself.

## 2. Non-goals
- No control setpoints, no "autopilot" language. Everything is advisory.
- No authentication, accounts, or live rig connection.
- No claims beyond the public data: no downhole vibration, no fleet-scale ROP gains.
- **[v0.2]** No WOB/RPM/mud-weight recommendation engine; no geomechanics/shale-reactivity model;
  no multi-rig benchmarking; no "% NPT reduction" claims; no comparisons to named vendor products.

## 3. Screens
Priority: **P0** must exist for the demo · **P1** strong differentiators · **P2** after physics backend.
Full per-screen detail: `06_SCREENS.md`.

### P0
- **S1 Field overview** — every wellbore (Volve + FORGE): name, field, years, MD range, hole sections; coverage
  matrix (time logs, depth logs, daily reports, formation tops, survey, mud) as cells with fill + glyph; QC score;
  confidence badge; filters by field and coverage; row click → S2.
- **S2 Well workspace** — depth-vs-time chart (hole sections shaded, casing points); synchronized tracks on one
  time axis: rig-state ribbon (rotary drilling, sliding, connection, trip in, trip out, reaming, circulating,
  out of hole, unknown), sensor tracks (hookload, block position, WOB, RPM, torque, SPP, flow in), daily-report
  activity lane, mismatch markers (click → side-by-side sensor vs report); linked cursor across all tracks;
  gaps hatched never interpolated; zoom from full well to one connection.
- **S3 Performance & invisible lost time** — KPI cards (connection time slips-to-slips and weight-to-weight;
  tripping speed in/out, cased/open hole; flat time; on-bottom %), distributions with composite-best line,
  lost-time waterfall, breakdown by section and day, outlier click → S2.
  **[v0.2]** + ILT definition panel and Reproduce panel (PR-1), + Booked-vs-measured panel (PR-2).
- **S4 Copilot panel** — docked on every screen, context-aware (well, time range, depth). Answer cards with
  Answer, Evidence from data (each number linked), Evidence from daily reports (quotes with well+date),
  Reasoning, Assumptions, Confidence (H/M/L + reason). Every number clickable → provenance (tool, params,
  source file, channel, window). Verifier failures flagged red. Tool-trace drawer. Suggested questions per
  screen. Honest "insufficient data" answer.
- **S5 Trust page** — data QC per well (gaps, spikes, unit fixes, sentinels); rig-state agreement with DDR per
  well; ablation table (no tools / simple RAG / full / full − physics) vs expert gold answers; known
  limitations; positioning vs the TADI paper. **[v0.2]** + field-level reconciliation matrix (PR-2), model
  cards (PR-3, PR-4), positioning vs standard industry practice.

### P1
- **S6 Formation view** — depth tracks: formation tops, lithology, ROP, MSE, d-exponent, gas, MW + ECD; problem
  events pinned at depth; offset comparison; per-formation summary; "Generate formation brief" (copilot).
  **[v0.2]** + predicted-vs-picked formation track with abstention (PR-3), precursor-signature panel (PR-4).
- **S7 Issue catalogue** — filterable table of geolocated events with links to report excerpt and S2 window;
  summary by formation and type.
- **S8 Replay mode (inside S2)** — historical stream at 1×/10×/60×; rig state, KPIs, alerts update live; toasts +
  event log.

### P2
- **S9 Torque & drag broomstick** (FORGE 16A), **S10 MSE & bit runs**, **S11 Trip-speed envelope** (PR-6).

## 4. Cross-cutting requirements (P0)
Provenance on hover for every computed number · confidence badges from data density (same rules as copilot) ·
units toggle metric/oilfield (m/ft, kN/klbf, bar/psi, m/h/ft/h, L/min/gpm, sg/ppg, kN·m/kft·lbf) app-wide ·
time and depth selection sync across views · server-side min/max-preserving downsampling and canvas rendering,
smooth pan/zoom at 1 Hz over 30+ days · static demo mode with pre-computed data and recorded copilot sessions,
live mode when an API is configured · dark control-room theme default + light theme; colour never the only
carrier of meaning · deep links: every view state in the URL.

## 5. Data contracts
See `04_DATA_CONTRACTS.md`. v0.1 endpoints: `/wells`, `/wells/{id}/channels`, `/rigstate`, `/ddr`,
`/mismatches`, `/kpis`, `/formations`, `/issues`, `POST /copilot/ask` (SSE), `/evidence/{id}`,
`WS /replay/{well}`, `/eval`. v0.2 additions in §11.

Copilot answer schema: `answer, claims[] {text, value, unit, evidence_id, verified}, ddr_quotes[] {well, date,
text}, reasoning, assumptions[], confidence, confidence_reason, trace[]`.

## 6. Stack
React + TypeScript + Vite · uPlot (tracks) · ECharts (stats) · TanStack Query · Zustand · Tailwind + tokens ·
FastAPI backend; static mode reads the same shapes from exported files.

## 7. Three-minute demo script (P0 acceptance test)
1. Field overview: "~20 public wellbores, with their gaps shown honestly."
2. Open the richest Volve well's workspace: zoom into one connection; ribbon, sensors and report lane line up;
   click a mismatch marker.
3. Performance: lost-time waterfall shows "X hours of lost time vs composite best"; click an outlier → S2.
4. Copilot: "What drove the lost time in the 12¼″ section?" → evidence cards; click a number → provenance;
   open the tool trace.
5. Trust page: ablation table and limitations.
6. (If P1) Replay at 60× with alerts firing.
P0 is done when this runs end to end in static mode, from a fresh clone, with no API key.

## 8. Build order
Shell/routing/theme/units/stores on mock JSON in final shapes → S1 → S2 → S3 → S4 (recorded, then live) → S5 →
P1 → P2. Fixtures are generated from the contracts first so front end and pipeline can proceed in parallel.

## 9. [v0.2] Decisions on v0.1 gaps
| Gap | Decision |
|---|---|
| No hole-section/casing contract | Add `GET /wells/{id}/sections`. |
| Time↔depth sync undefined | Add `GET /wells/{id}/depthtime`; depth→time = set of intervals where hole depth crosses that depth. |
| Static mode vs 1 Hz × 30 days | Export a min/max pyramid as binary chunks; JSON only for metadata/intervals/answers. |
| Where confidence is computed | Pipeline/backend only; front end renders it. |
| Units vs verifier | Claims stay SI; `<Num>` converts for display; provenance shows source value + unit. |
| Recorded sessions catalogue | Add `GET /copilot/sessions`; static-mode suggestions come only from it. |
| Evidence ID scope | Every computed number in every contract is a `Quantity {value, unit, evidence_id}`. |
| Gap masks shape | Per-channel intervals `[t0, t1, reason]`, reason ∈ no_data, removed_spike, sentinel, unit_fix. |
| Mismatch semantics | Backend applies tolerance (boundary slack, min duration) and emits overlap %; UI only renders. |
| Gold answers undefined | S5 ships the table schema with explicit gold-set header; empty state says so. |

## 10. [v0.2] Proposals beyond standard industry practice
Context: `09_INDUSTRY_REVIEW.md`. Standard practice (rig-state KPIs, ILT dashboards, DDR integration, tree-ensemble
hazard/ROP models) is replicated; STRATA differentiates on reproducibility, measured disagreement, honest
validation and verified AI answers.

| ID | Proposal | Pages | Contract | Prio |
|---|---|---|---|---|
| PR-1 | Reproducible invisible lost time: published definition (composite best = P10 per KPI per section; gap-overlapping intervals excluded), per-category/section/day results, Reproduce panel (commit, data hashes, one command). | S3, S5, S4 tool `kpi.ilt` | `/wells/{id}/ilt`, `/meta/repro` | P0 |
| PR-2 | Measured sensor↔report reconciliation: DDR code × measured rig state → minutes and %, agreement per well, tolerance shown. | S2 lane, S3 panel, S5 matrix | `/reconciliation`, `/wells/{id}/mismatches` | P0 |
| PR-3 | Formation classification from surface drilling response (ROP, MSE, torque, d-exp, gas), leave-one-well-out validation, calibrated, vs depth-only baseline, abstains when uncertain. | S6 track, S5/S6 model card | `/models/formation/card`, `/wells/{id}/formation-pred` | P1 |
| PR-4 | Event retrieval + precursor signatures (stuck pipe, losses, tight hole) from DDR narratives; 6 h channel windows vs normal band. Explicitly not a risk score. | S6 pins+panel, S7, S2 jump | `/issues`, `/issues/{id}/precursors` | P1 |
| PR-5 | Verified copilot with ablations (v0.1) + positioning panel. | S4 (all pages), S5 | `/copilot/ask`, `/eval` | P0 |
| PR-6 | Physics next to statistics: T&D friction factor, MSE per bit run, trip speed vs surge/swab envelope. | S9–S11 | `/wells/{id}/td`, `/mse`, `/tripenvelope` | P2 |

## 11. [v0.2] Contracts added
`GET /wells/{id}/sections` · `GET /wells/{id}/depthtime` · `GET /wells/{id}/ilt` · `GET /meta/repro` ·
`GET /reconciliation?well=` · `GET /models/formation/card` · `GET /wells/{id}/formation-pred` ·
`GET /issues/{id}/precursors` · `GET /copilot/sessions`.
