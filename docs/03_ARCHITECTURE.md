# Architecture

## 1. Repository layout (target)
```
drilling_copilot/
├── CLAUDE.md                     agent instructions
├── Makefile                      single entry point for every command
├── contracts/
│   ├── schemas/strata.schema.json    SOURCE OF TRUTH for every payload ($defs per type)
│   ├── endpoints.yaml                endpoint → request params → response $def
│   └── codegen/                      scripts: TS types, zod, Pydantic
├── apps/web/                     React + TS + Vite front end
│   ├── public/data/              static-mode export (fixtures first, real exports later)
│   ├── src/
│   │   ├── app/                  shell, router, providers, layout, nav
│   │   ├── contracts/            GENERATED types + zod (do not edit)
│   │   ├── data/                 DataSource interface, StaticSource, HttpSource, query hooks, series decoder
│   │   ├── state/                Zustand stores: view (URL-synced), cursor, prefs, replay
│   │   ├── units/                unit registry + conversion
│   │   ├── trust/                Num, ConfidenceBadge, EvidencePopover, MockBadge, InsufficientData, Limitation
│   │   ├── charts/               uPlot: TrackStack, DepthTime, plugins/*; ECharts: KpiDist, Waterfall, …
│   │   ├── copilot/              CopilotDock, AnswerCard, ToolTrace, Suggestions, session player
│   │   ├── screens/              S1Field, S2Workspace, S3Performance, S5Trust, S6Formation, S7Issues, S9–S11
│   │   └── styles/               tokens.css (dark/light), tailwind.css
│   └── e2e/                      Playwright demo-script test
├── pipeline/                     Python package `strata_pipeline`
│   ├── ingest/                   volve_witsml.py, volve_ddr.py, forge.py, tops.py, survey.py, mudlog.py
│   ├── qc/                       gaps, spikes, sentinels, units, qc_score
│   ├── rigstate/                 rules classifier, smoothing, confidence
│   ├── kpi/                      connections, trips, flat_time, on_bottom, composite_best, ilt
│   ├── recon/                    DDR code mapping, mismatches, reconciliation matrix
│   ├── formation/                features, classifier (LOWO), card            (P1)
│   ├── events/                   DDR narrative extraction, geolocation, precursors (P1)
│   ├── physics/                  mse, dexp, torque_drag, surge_swab           (MSE/dexp P1, rest P2)
│   ├── evidence.py               evidence registry (every number gets an id)
│   ├── confidence.py             the ONLY confidence rules implementation
│   └── export/                   json writers, series pyramid writer, repro manifest
├── services/api/                 FastAPI app `strata_api` (live mode)
│   ├── routes/                   one module per endpoint group, typed by generated Pydantic models
│   └── copilot/                  tools.py, agent.py (LLM loop), verifier.py, recorder.py, sessions/
├── eval/                         gold questions, ablation runners, results → export
├── data/                         raw/ interim/ (gitignored); export/ → synced to apps/web/public/data
└── docs/
```

## 2. Data flow
```
raw public files ─ingest→ interim parquet (SI units, UTC, per well)
   ─qc→ cleaned parquet + gap intervals + QC report
   ─rigstate→ state intervals (+confidence)
   ─kpi/ilt/recon/formation/events/physics→ result tables, each value registered in evidence registry
   ─export→ data/export/** (JSON + binary series pyramid + evidence + repro manifest)
            ├─ copied to apps/web/public/data  → StaticSource (no server)
            └─ served by services/api          → HttpSource (live mode, same shapes)
```
Rule: the API never recomputes analytics on request in P0; it serves the export (plus copilot and replay).
This guarantees static mode and live mode show identical numbers.

## 3. Front-end architecture
### 3.1 DataSource
```ts
interface DataSource {
  wells(): Promise<WellList>;
  sections(id: WellId): Promise<Section[]>;
  depthTime(id: WellId): Promise<DepthTimeBlock>;
  seriesIndex(id: WellId): Promise<SeriesIndex>;
  seriesChunk(id: WellId, ch: ChannelId, level: number, chunk: number): Promise<SeriesChunk>;
  rigState(id: WellId, t0: number, t1: number): Promise<RigStateInterval[]>;
  ddr(id: WellId, t0: number, t1: number): Promise<DdrActivity[]>;
  mismatches(id: WellId): Promise<Mismatch[]>;
  kpis(id: WellId): Promise<KpiReport>;
  ilt(id: WellId): Promise<IltReport>;
  reconciliation(id?: WellId): Promise<Reconciliation>;
  formations(id: WellId): Promise<FormationReport>;
  formationPred(id: WellId): Promise<FormationPrediction>;
  modelCard(model: 'formation' | 'events'): Promise<ModelCard>;
  issues(q: IssueQuery): Promise<Issue[]>;
  precursors(issueId: string): Promise<Precursors>;
  evidence(id: EvidenceId): Promise<Evidence>;
  sessions(): Promise<SessionIndex>;
  ask(question: string, ctx: CopilotContext, sessionId?: string): AsyncIterable<CopilotEvent>;
  replay(id: WellId, speed: 1 | 10 | 60, fromT: number): AsyncIterable<ReplayEvent>;
  evalReport(): Promise<EvalReport>;
  repro(): Promise<ReproManifest>;
}
```
`createDataSource()` returns `HttpSource(VITE_API_URL)` if set, else `StaticSource('/data')`. Every response is
validated with the generated zod schema in dev builds (and in tests); invalid payloads throw with the path.
StaticSource `ask()` replays `copilot/sessions/{id}.jsonl` honouring recorded `dt_ms`; a free-text question
with no matching session yields a single `answer` event of kind `live_mode_required`.
StaticSource `replay()` streams from the L0 series chunks + precomputed state/alert events with a timer.

### 3.2 State (Zustand)
- `useView` (URL-synced via `replaceState`, debounced 150 ms): `wellId, timeRange, depthRange, panel,
  sessionId, evidenceId, section, filters`. Back/forward restores state.
- `useCursor` (not in URL): `t: number | null`, updated through rAF; consumed by uPlot sync + readouts.
- `usePrefs` (localStorage, try/catch): `units: 'metric' | 'oilfield'`, `theme: 'dark' | 'light'`.
- `useReplay`: `playing, speed, t, log[]`.
URL scheme: `/field`, `/well/:id/workspace?t0&t1&panel&ev&s`, `/well/:id/performance?section`,
`/well/:id/formation?d0&d1&issue`, `/issues?well&type&formation`, `/trust`, `/well/:id/td|mse|trips`.

### 3.3 Charts
- **TrackStack** (uPlot): one instance per track, shared `cursor.sync.key = 'strata-time'`, shared x-scale set
  via `setScale` broadcast, fixed left gutter width so every track and the ribbon/lane align.
- Plugins (uPlot `hooks.draw`): `sectionsPlugin`, `gapHatchPlugin`, `ribbonPlugin` (dominant state per pixel
  column when intervals < 1 px; pattern fills from design tokens), `ddrLanePlugin`, `mismatchPlugin`
  (hit-testing for clicks), `cursorReadoutPlugin`.
- Series: draw min and max as a filled band + mid line, so spikes survive downsampling.
- **DepthTime**: uPlot with inverted y; same x-scale; overview mini-chart with brush for full well.
- ECharts for S3/S5 statistics (boxplot, waterfall via stacked bars, heatmap for reconciliation).
- Theme: charts read CSS variables at mount and on theme change (re-instantiate).

### 3.4 Series LOD pyramid (static + live)
Levels L0…L6 with bucket sizes 1, 8, 64, 512, 4096, 32768, 262144 s. Each bucket stores min and max.
Chunk duration per level: L0 6 h, L1 48 h, L2+ whole well. File: `wells/{id}/series/{ch}/L{n}/{chunk}.bin`,
little-endian: header `u32 magic 'STRS', u32 n, f64 t0_epoch_ms, f32 bucket_s` then `f32[n] min, f32[n] max`
(NaN = gap). Level choice: smallest level with `(t1 − t0)/bucket_s ≤ 2 × plotWidthPx`.
Live mode `GET /wells/{id}/channels?ch&start&end&px` returns the same binary block.

## 4. Backend
- FastAPI, routes generated-model typed; serves `data/export` for all GET endpoints in P0.
- `/copilot/ask`: SSE stream of `CopilotEvent` (see contracts). Agent loop = Anthropic Messages API with
  tool use; tools are thin wrappers over export tables/evidence (no free SQL). Final answer must be emitted
  through a `submit_answer` tool whose input is the `CopilotAnswer` schema; the verifier then checks each claim.
- **Verifier**: for each claim, load `evidence_id`; require unit match (after SI normalization) and
  `|claim.value − evidence.value| ≤ display tolerance` (rounding to the precision shown); claims without
  evidence or failing the check get `verified=false`; numbers in `answer`/`reasoning` text that are not
  claims are also extracted (regex) and flagged.
- **Recorder**: in live mode every session can be saved as JSONL into `copilot/sessions/`; recorded sessions
  ship with the static export and drive static-mode suggestions.
- `WS /replay/{well}`: server streams L0 samples + state transitions + alert events at speed.

## 5. Evidence and confidence
- `pipeline/evidence.py` assigns `ev_<sha1(tool|params|source|window)[:10]>` to every exported number and writes
  `evidence/{id}.json` (static: sharded `evidence/{prefix}.json`, 256 shards).
- `pipeline/confidence.py` implements rules from `07_DATA_AND_ALGORITHMS.md §8`; used by QC, KPIs and the
  copilot tool outputs. The front end never computes confidence.
