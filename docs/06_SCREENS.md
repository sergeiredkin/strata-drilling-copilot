# Screens — detailed specs

Each screen: route · data · layout · interactions · states · acceptance. Comps: `docs/design/comps/<file>`.
Every screen shares the shell: nav, ModeBadge, units toggle, theme toggle (in a menu), Copilot dock toggle.
Global states for every data block: loading skeleton (no spinners over charts), error card with the failing
path, empty state that explains what is missing, MOCK badge when `is_mock`.

---
## S1 Field overview — `/field` (default route) · comp `S1-Field.dc.html` · P0
Data: `wells()`.
Layout: page header (count, sources sentence, MockBadge) → filter bar (search, Field: All/Volve/FORGE,
Needs: Time logs / Daily reports, Hide low confidence) → legend (full/partial/none) → table → two explainer
cards (QC score formula, confidence rules link to S5).
Table columns: Wellbore (link) · Field · Years · MD range · Hole sections · 6 coverage cells · QC score
(bar + `<Num>`) · Confidence badge. Sortable by name, QC, confidence. Whole row clickable (link in first cell
is the accessible target).
Interactions: coverage cell hover → rows, date span, source files. Row click → `/well/:id/workspace` at the
richest default window (first full day of the longest-coverage section). Filters reflected in URL.
Acceptance: all wells render; filters combine (AND); low-confidence rows remain visible unless the toggle is on;
keyboard navigable; 20 rows render < 50 ms.

---
## S2 Well workspace — `/well/:id/workspace?t0&t1&panel&ev&s` · comp `S2-Workspace.dc.html` · P0
Data: `sections, depthTime, seriesIndex + chunks, rigState, ddr, mismatches`, copilot sessions.
Layout (top→bottom, left column flex 999 1 760px; copilot dock right):
1. Header: well id, ConfidenceBadge, breadcrumb (Full well › section › day › window), zoom −/+, "Fit
   connection", Replay button (disabled until P1), MockBadge.
2. Overview strip (64 px): full-well depth-vs-time, section shading with labels, casing ▼ markers, brush
   rectangle = current window (drag to move, edges to resize).
3. Track stack (shared x-axis, gutter 148 px with label/unit/readout at cursor):
   bit depth vs time (150 px, inverted y) → rig-state ribbon (40 px) → DDR lane (36 px, bars with code +
   narrative truncated) with mismatch ▲ markers → HKLD, BPOS, WOB, RPM, TORQ, SPP, FLOWIN (54 px each,
   min/max band + line) → time axis.
4. Overlays across the whole stack: gap hatching with "no data · N min" label; cursor line + time chip.
5. Legend for rig states.
Interactions:
- Hover anywhere → `useCursor.t`; all tracks show a vertical line and readouts; depth chart dot.
- Wheel/pinch = zoom around cursor; drag = pan; double-click = zoom to the rig-state interval under cursor;
  "Fit connection" = zoom to the nearest connection ±2 min. Range limits: 2 min … full well.
- Mismatch marker click → popover: Sensors say (state, rule summary, p) | Report says (code, narrative quote,
  DDR date + time); overlap % and tolerance; buttons "Zoom to window", "Ask copilot why" (prefills dock with
  context = mismatch window).
- Brush/zoom updates URL `t0,t1` (debounced). Opening a deep link restores the exact window.
Performance: 30-day well, 7 channels: initial render < 1.5 s on a mid laptop; pan/zoom ≥ 50 fps; never more than
~2 buckets per pixel drawn.
Acceptance: demo beat 2 passes (zoom into one connection, ribbon/sensors/lane align to the pixel at the same t,
mismatch popover shows both versions); gaps hatched and series broken; units toggle changes axis units and
readouts without refetch.

---
## S3 Performance & invisible lost time — `/well/:id/performance?section` · comp `S3-Performance.dc.html` · P0
Data: `kpis, ilt, reconciliation(id), repro`.
Layout: header + section filter chips (All, per hole size) → 4 KPI cards (Connection time, Tripping speed,
Flat time, On-bottom %; each value `<Num>`, sub-line, best, confidence) → row: connection-time box plots per
section with composite-best dashed line and clickable outliers | lost-time waterfall (categories → total) with
"booked as NPT in DDR" comparison → row: by-section table | by-day bars (hatched when coverage < 60 %) →
**[v0.2]** row: Booked-vs-measured bars per DDR code (PR-2) | "How lost time is defined" + Reproduce panel (PR-1).
Interactions: outlier dot / day bar / booked-vs-measured segment → S2 at that window (deep link). KPI card
click → filters the distribution chart to that KPI. "Copy command" copies `make reproduce WELL=<id>`.
Acceptance: demo beat 3; waterfall total equals Σ categories equals Σ by-section equals Σ by-day (unit test on
export, and UI test); every number has evidence.

---
## S4 Copilot dock — available on every screen · comp inside `S2-Workspace.dc.html` · P0
Data: `sessions()`, `ask()`, `evidence()`.
Layout: header (Copilot, "recorded session"/"live" badge) → context line (well · section · window · depth) →
conversation (question bubble → Tool trace button "▸ Tool trace · N calls · X s" → AnswerCard) →
Suggested questions (from sessions matching screen+well in static mode; generated per screen in live mode) →
input (disabled with explanatory placeholder in static mode when no session matches).
AnswerCard sections: Answer · Evidence from data (claim text + `<Num>` per claim; red when unverified; footer
"✕ N numbers failed the verifier") · Evidence from daily reports (quotes + well + date, click → S2 at DDR row) ·
Reasoning · Assumptions · Confidence badge + reason. Kinds: `insufficient_data` (what is missing + which data
would answer it), `live_mode_required`, `out_of_scope` (e.g. setpoint questions → explains advisory scope).
Tool trace drawer: ordered steps with tool, args (mono), ms, status, result summary, evidence ids.
Streaming: show trace steps as they arrive; AnswerCard appears on `answer` event.
Acceptance: demo beat 4; a recorded session with one unverified number renders it red; every claim's popover
resolves; dock state (open, session) is in the URL.

---
## S5 Trust page — `/trust` · comp `S5-Trust.dc.html` · P0
Data: `evalReport, reconciliation('all'), modelCard('formation'), modelCard('events'), repro`.
Layout: header → row: Data QC per well table (gap hours, spikes, unit fixes, sentinels, rig-state agreement bar)
| Known limitations list → Ablation table with gold-set header (empty state when `status = pending`) →
**[v0.2]** row: reconciliation heatmap matrix (DDR code × measured state, diagonal green, off-diagonal ≥10 %
amber) | Model cards (formation, events) → Positioning vs standard industry practice table → Positioning vs TADI
→ Reproduce manifest (commit, file hashes).
Acceptance: demo beat 5; no placeholder scores are shown as real numbers (null → "—" with reason).

---
## S6 Formation view — `/well/:id/formation?d0&d1&issue&offset` · comp `S6-Formation.dc.html` · P1
Data: `formations, formationPred, depthTime, issues(well), precursors(issue), modelCard('formation')`,
depth-indexed channels (ROP, MSE, d-exp, GAS, MW_IN, ECD) from the depth series export.
Layout: header (single well / offset compare toggle, "Generate formation brief", MockBadge) → depth grid:
MD scale · Tops (picked) · Predicted (PR-3; abstained = hatched; disagreement = red) · Lithology · ROP · MSE ·
d-exp · Gas · MW+ECD (ECD dashed) · Events column (SP/LC/TH/KC buttons) → right panel: selected event
(excerpt, precursor small multiples −6 h → event with normal band, "Open window in Workspace", "Ask copilot") +
model card summary → per-formation summary table (avg ROP, avg MSE, incidents, best window **advisory**, wells,
confidence).
Offset compare: up to 4 wells side by side, aligned on formation tops (flattened) with a toggle to MD.
"Generate formation brief" → copilot with context screen=formation → AnswerCard titled "Pre-spud brief: <fm>".
Acceptance: depth↔time link: clicking an interval opens S2 at the corresponding time intervals; abstention and
disagreement visually distinct without colour (pattern + label in tooltip).

---
## S7 Issue catalogue — `/issues?well&type&formation` · no comp yet (build from S1 table patterns) · P1
Table: type, well, date, MD, formation, section, duration, MW/ECD at time, extraction method; row actions:
report excerpt popover, "Open in Workspace", "Open in Formation". Summary view: matrix formation × type counts.

## S8 Replay (inside S2) — `?replay=1&speed=60` · P1
Controls in S2 header: play/pause, 1×/10×/60×, time readout. Track window follows the replay head (last
30 min). Rig state and running KPIs update; alerts (slow connection > composite best × 1.5, unreported reaming,
flat time > 15 min, data gap) appear as toasts (max 3 visible) and in an event log drawer. Same reducer for
static (timer) and live (WS).

## S9 T&D broomstick · S10 MSE & bit runs · S11 Trip envelope — P2
S9: hookload vs depth with pick-up/slack-off points and model lines for FF 0.15…0.40; FF trend vs depth (16A).
S10: MSE vs depth per bit run, run boundaries from BHA records, efficiency trend.
S11: trip speed vs depth vs surge/swab-limited envelope; breaches highlighted and linked to S2.

---
## Function → page map
| Function | Primary | Also on | Prio |
|---|---|---|---|
| Well table, coverage, QC, confidence | S1 | S5 | P0 |
| Depth-vs-time, sections, casing | S2 | S6 (depth link) | P0 |
| Rig-state ribbon + legend | S2 | S8 | P0 |
| Sensor tracks, cursor, zoom, gap hatching | S2 | S6 | P0 |
| DDR lane + mismatch popover (PR-2) | S2 | — | P0 |
| KPI cards, distributions, composite best, waterfall | S3 | S4 | P0 |
| ILT definition + Reproduce (PR-1) | S3 | S5 | P0 |
| Booked vs measured (PR-2) | S3 | S5 matrix | P0 |
| Copilot dock, provenance, verifier, trace | S4 | every page | P0 |
| Insufficient-data / out-of-scope cards | S4 | every page | P0 |
| QC, agreement, ablation, limitations, positioning | S5 | — | P0 |
| Model cards (PR-3/4) | S5 | S6 | P1 |
| Formation tracks, predicted track (PR-3) | S6 | — | P1 |
| Event pins + precursors (PR-4) | S6 | S7, S2 | P1 |
| Offset compare + formation brief | S6 | S4 | P1 |
| Issue catalogue | S7 | S6 | P1 |
| Replay + alerts | S8 (S2) | — | P1 |
| T&D, MSE runs, trip envelope (PR-6) | S9–S11 | S6, S3 | P2 |
| Units, theme, deep links, provenance hover, confidence, mode badge | global | all | P0 |
