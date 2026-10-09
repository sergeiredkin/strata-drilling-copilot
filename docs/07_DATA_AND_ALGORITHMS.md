# Data sources and algorithms

Everything here is a v1 definition owned by STRATA. Each definition is shown in the UI where its numbers
appear (S3 "How lost time is defined", S5). Thresholds live in `pipeline/strata_pipeline/config.yaml`, never
hard-coded, and are recorded in each Evidence `params`.

## 1. Data sources (verify before ingesting)
| Source | What we expect to use | Notes |
|---|---|---|
| **Equinor Volve data village** (released 2018) | WITSML real-time drilling data (time- and depth-indexed logs), daily drilling reports (XML), well technical data, formation tops / picks, surveys, mud logs, BHA/bit records where present | **T2.1 must confirm** folder structure, which wellbores have time-indexed 1 Hz-ish logs, timestamp time zone, and the licence terms; record findings in `docs/DATA_INVENTORY.md` and licence text in `docs/LICENSES.md`. |
| **Utah FORGE** (Geothermal Data Repository) | Drilling data (EDR time logs), daily drilling reports, surveys and well reports for 16A(78)-32, 16B(78)-32, 58-32, 78B-32 as available | Same verification; granite geothermal wells — never benchmarked against Volve without a label. |
Raw files go to `data/raw/<source>/…` (gitignored) with a `data/raw/MANIFEST.json` (url, sha256, bytes,
downloaded_at). Download scripts must be idempotent and resumable. Never commit raw data.

## 2. Ingestion → interim parquet (per well)
- `time.parquet`: columns `t_ms` + canonical channels (HKLD kN, BPOS m, WOB kN, RPM rpm, TORQ kN.m, SPP bar,
  FLOWIN L/min, BITDEPTH m, HOLEDEPTH m, ROP m/h, MW_IN sg, ECD sg, GAS %); original mnemonic + unit recorded in
  `channels.json` (mnemonic map in `pipeline/strata_pipeline/ingest/mnemonics.yaml`).
- `depth.parquet`: 0.5 m bins of depth-indexed logs.
- `ddr.parquet`: one row per activity: t0, t1, raw code, normalized code, md_from, md_to, narrative, report date,
  npt flag.
- `tops.parquet`, `survey.parquet` (MD, inc, azi → TVD/N/E by minimum curvature), `sections.parquet`
  (from casing/hole-size records; fallback: DDR narratives + bit size changes; source recorded).

## 3. QC (per channel)
1. Unit detection & fix by plausible ranges (e.g. hookload median > 1500 ⇒ assume lbf → convert; SPP > 600 ⇒ psi).
   Each fix logged as `unit_fix` with the rule.
2. Sentinels: −999.25, −9999, 9999, NaN strings → gap(`sentinel`).
3. Spikes: Hampel filter, window 31 samples, threshold 6·MAD → gap(`removed_spike`) (single samples only).
4. Frozen values: dynamic channel constant (non-zero) > 300 s → gap(`frozen_value`).
5. Resample to 1 s grid without filling; holes > 5 s become gap(`no_data`).
6. QC report per well: gap hours per channel, counts per reason, fraction of samples surviving.
**QC score** = coverage_weighted × (1 − core_gap_fraction) × survived_fraction, where coverage weights are
time logs .35, daily reports .20, depth logs .15, tops .10, survey .10, mud .10 (full=1, partial=.5, none=0);
core channels = HKLD, BPOS, FLOWIN, RPM, BITDEPTH, HOLEDEPTH.

## 4. Rig-state classifier (rules, deterministic)
Pre-processing: 5 s median filter on inputs; block velocity v = dBPOS/dt (5 s centred).
Per-well calibration: slips threshold `HL_slips` = valley between the two modes of the hookload histogram
(fallback: travelling-block weight + 15 %); recorded in evidence params.
Flags: `on_bottom` = HOLEDEPTH − BITDEPTH ≤ 0.5 m · `in_slips` = HKLD < HL_slips · `rotating` = RPM > 5 ·
`pumping` = FLOWIN > 100 L/min · `moving` = |v| > 0.05 m/s · `near_bottom` = HOLEDEPTH − BITDEPTH < 40 m.
Rules (first match wins; `rule_id` stored):
| # | Condition | State |
|---|---|---|
| R0 | any core channel in gap | unknown |
| R1 | BITDEPTH < 30 m and not pumping | out_of_hole |
| R2 | in_slips and near_bottom | connection |
| R3 | in_slips and not near_bottom | trip_in / trip_out (direction of the enclosing trip) |
| R4 | on_bottom and pumping and rotating | rotary_drilling |
| R5 | on_bottom and pumping and not rotating | sliding |
| R6 | not on_bottom and pumping and rotating and moving | reaming (v>0 ⇒ back-reaming flag) |
| R7 | not on_bottom and pumping | circulating |
| R8 | not on_bottom and not pumping and moving and v<0 | trip_in |
| R9 | not on_bottom and not pumping and moving and v>0 | trip_out |
| R10 | otherwise | unknown (rule `idle`) |
Trip direction for R3/R8/R9 smoothing: sign of net BITDEPTH change over a 10-min window. Post-processing:
merge intervals < 10 s into neighbours (hysteresis), except connection. `cased_hole` = BITDEPTH < last casing
shoe MD. Interval confidence `p` = share of samples whose deciding inputs are > 10 % away from thresholds.
Validation: (a) agreement with DDR (§7); (b) hand-labelled gold sample of 200 random 10-min windows in
`eval/rigstate_gold.csv` (labelled by Sergei) → per-state precision/recall on S5.

## 5. KPIs
- **conn_s2s** — duration of each R2 connection interval (in slips).
- **conn_w2w** — from last sample with WOB > 5 kN on bottom before the connection to first such sample after it.
- **Trip speed** — trips = maximal blocks of trip_in/trip_out allowing in-slips gaps ≤ 10 min; speed = |ΔBITDEPTH|
  / elapsed h, split into cased/open by the casing shoe; per-stand speeds for distributions.
- **flat_time_pct** — time in circulating, reaming, unknown(idle) and out_of_hole ÷ total valid time.
- **on_bottom_pct** — (rotary_drilling + sliding) ÷ total valid time.
- **Composite best** — P10 of durations / P90 of speeds, per KPI per hole section per well; requires n ≥ 10,
  else falls back to well level and confidence drops to low.
- Distributions report min, q1, median, q3, max, outliers (> q3 + 1.5 IQR) with their windows.

## 6. Invisible lost time (PR-1)
```
ILT_connections = Σ_conn max(0, d_conn − best_conn(section))
ILT_trips       = Σ_trip max(0, t_trip − distance_trip / best_speed(section, cased|open))
ILT_flat        = Σ circulating/idle minutes inside DDR rows coded DRILL or TRIP (flat time not booked as such)
ILT_reaming     = Σ reaming minutes inside DDR rows coded DRILL (unreported reaming)
ILT_total       = sum of the four; intervals overlapping a gap are excluded and summed in excluded_gap_hours
```
`booked_npt` = Σ DDR rows with npt = true, shown next to ILT ("booked as NPT in DDR"). By-day and by-section
breakdowns must sum exactly to the total (test).

## 7. Reconciliation (PR-2)
DDR code normalization map in `pipeline/strata_pipeline/recon/ddr_codes.yaml` (raw Volve/FORGE activity codes →
DRILL, CIRC, TRIP, REAM, CASING, CEMENT, BOP, WAIT, OTHER). Expected sensor states:
DRILL → {rotary_drilling, sliding, connection} · CIRC → {circulating} · TRIP → {trip_in, trip_out} ·
REAM → {reaming, circulating}; CASING/CEMENT/BOP/WAIT/OTHER excluded from agreement.
Tolerance: ignore ±5 min at every DDR row boundary; a mismatch is a contiguous run ≥ 2 min of sensor states
outside the expected set. Matrix cell = minutes of measured state within booked code (outside slack) and % of row.
Agreement per code = diagonal share; per well = minute-weighted mean over included codes.

## 8. Confidence rules (`pipeline/confidence.py`, the only implementation)
| Rule | high | medium | low | insufficient |
|---|---|---|---|---|
| C1 core-channel coverage in window | ≥ 0.90 | ≥ 0.60 | > 0 | 0 |
| C2 sample size for statistic | n ≥ 30 | 10–29 | 1–9 | 0 |
| C3 mean rig-state p in window | ≥ 0.85 | ≥ 0.70 | < 0.70 | — |
| C4 DDR coverage (only for DDR-dependent numbers) | ≥ 0.90 | ≥ 0.60 | > 0 | 0 |
Level = lowest across applicable rules; `reason` = human sentence for the binding rule;
`rule_ids` lists them. Copilot tools return the same object; the copilot's answer confidence = lowest of its
claims' confidences unless it explains otherwise.

## 9. Formation classifier (PR-3, P1)
Features at 1 m MD bins: ROP, MSE, surface torque, WOB, RPM, d-exponent (corrected), total gas, plus rolling
mean/std over 5 and 20 m. Label: formation from picked tops. Model: scikit-learn HistGradientBoostingClassifier,
isotonic calibration fitted inside each training fold. **Validation: leave-one-well-out** across wells with
tops; never random splits. Baseline: classifier on TVD only. Abstain when max p < τ, τ chosen inside training
folds for ≥ 0.9 precision. Optional: enforce stratigraphic order with a left-to-right HMM/Viterbi decode
(report both). Report macro-F1, accuracy, ECE, abstain rate, per-well F1; export predictions for held-out wells
only (`held_out=true`).

## 10. Events and precursors (PR-4, P1)
Extraction from DDR narratives: rule lexicon first (stuck|pipe stuck|work(ed)? pipe free|jar(red|ring)?|
overpull|tight|pack(ed)? off|loss(es)?|lost circulation|LCM|kick|influx|gain) → candidates; optional LLM pass
with structured output that must return the quoted span; manual review CSV for a 50-event sample →
extraction precision on the model card. Geolocate MD from DDR md fields or BITDEPTH at event start.
Precursors: 6 h before event start for HKLD, TORQ, SPP (+ pick-up weights from trip connections);
normal band = P10–P90 of the same channel in rotary_drilling/trip windows within ±50 m MD in the same well and
offsets. **No risk score** is computed or shown.

## 11. Physics
- MSE (Teale): `MSE = WOB/A + 2π·N·T / (A·ROP)` in SI (N, m², rev/s, N·m, m/s) → MPa; surface torque used
  (limitation stated).
- d-exponent (Jorden & Shirley): `d = log10(R/(60N)) / log10(12W/(10^6·D))` with R ft/h, N rpm, W lbf, D in;
  `dxc = d · (ρ_normal / ECD)`, ρ_normal configurable (default 1.03 sg, verify).
- P2: soft-string torque & drag (Johancsik) using minimum-curvature survey, FF sweep 0.15–0.40; surge/swab
  screening envelope (simplified steady-state model, labelled "screening").

## 12. Copilot tools (live mode; same tools used to record static sessions)
`list_wells`, `well_summary(well)`, `rigstate_summary(well, t0, t1)`, `kpi_connection_times(well, section, stat)`,
`kpi_trips(well, section, direction, hole)`, `ilt_breakdown(well, by)`, `reconciliation(well)`,
`mismatches(well, t0, t1)`, `ddr_search(well, query, t0?, t1?)` (BM25 over narratives; returns row ids + text),
`formation_stats(well, formation)`, `issues_query(...)`, `evidence(id)`, `submit_answer(CopilotAnswer)`.
Every tool returns values as Quantities with evidence ids. System prompt rules: use only tool numbers; every
number in the answer must appear as a claim with its evidence id; say `insufficient_data` when tools return
insufficient confidence; refuse setpoint recommendations with `out_of_scope`.

## 13. Evaluation
- Gold set `eval/gold/questions.yaml`: id, question, context, expected key numbers (with evidence ids or
  tolerance), expected kind (answer / insufficient_data / out_of_scope), rubric notes. Authored by Sergei;
  status pending until ≥ 25 questions.
- Ablations: `no_tools` (LLM only with well list), `simple_rag` (BM25 over DDR + exported tables as text),
  `full`, `full_minus_physics` (physics tools disabled). Metrics: answer correctness (rubric, 0–1), % numbers
  verified, unsupported numbers per answer, % correct insufficient_data, median latency.
