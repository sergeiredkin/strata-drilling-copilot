# Backlog (tick as done; order = critical path in docs/02_IMPLEMENTATION_PLAN.md §2)

## M0 Foundations
- [x] T0.1 Monorepo scaffold
- [x] T0.2 CI workflow
- [x] T0.3 Fonts, Tailwind, tokens (dark + light)
- [x] T1.1 Contract codegen (TS, zod, Pydantic) + contracts-check
- [x] T1.2 Fixture generator (3 detailed wells + 6 summary wells, sessions, eval, repro)
- [x] T1.3 STRS series pyramid writer + TS decoder
- [x] T4.1 DataSource (Static/Http) + query hooks + session player
- [x] T4.2 Stores, routing, URL sync, nav
- [x] T4.3 Units registry
- [x] T4.4 Trust kit (Num, EvidencePopover, badges, InsufficientData)

## M1 Workspace
- [x] T5.1 S1 Field overview
- [x] T6.1 TrackStack core (uPlot sync, gutter, zoom/pan)
- [x] T6.2 Plugins: gaps, sections, cursor
- [x] T6.3 Depth-vs-time + overview brush
- [x] T6.4 Ribbon, DDR lane, mismatches + popover
- [x] T6.5 S2 assembly

## M2 Performance & Copilot (static)
- [x] T7.1 S3 KPI cards, distributions, waterfall, by section/day
- [x] T7.2 S3 Booked-vs-measured, ILT definition, Reproduce (PR-1, PR-2)
- [x] T8.1 Copilot dock + AnswerCard + trace (static sessions)
- [x] T8.2 Copilot context plumbing

## M3 Trust + P0 e2e
- [x] T9.1 S5 Trust (incl. reconciliation matrix, model cards, positioning)
- [x] T10.1 Playwright demo-script e2e
- [x] T10.2 Performance budget test
- [x] T10.3 A11y + copy lint

## M4 Real data (Lane B)
- [x] T2.1 Data inventory + licences  ← reported to Sergei (see docs/DATA_INVENTORY.md, docs/LICENSES.md)
- [x] T2.2 Volve time-log ingest (witsml_time.py; sections derivation + tops still open — see docs/DATA_INVENTORY.md)
- [x] T2.3 Volve DDR ingest (ddr.py)
- [ ] T2.4 FORGE ingest ← blocked on OpenEI/GDR infrastructure outage, see docs/DATA_INVENTORY.md §4
- [x] T3.1 QC (strata_pipeline/qc/*; source reconciliation per docs/adr/0007)
- [x] T3.2 rig-state rules classifier + gold-sample agreement script (eval/strata_eval/rigstate_agreement.py; eval/rigstate_gold.csv pending Sergei's hand labels)
- [ ] T3.2 Rig-state classifier + gold-sample agreement
- [x] T3.3 KPIs + composite best (strata_pipeline/kpi/*; per-stand trip speed distributions deferred — see trips.py docstring)
- [x] T3.4 ILT (strata_pipeline/kpi/ilt/*)
- [x] T3.5 Reconciliation + mismatches (strata_pipeline/recon/*; ddr_codes.yaml now the shared normalization source for ingest + recon)
- [x] T3.6 Confidence module + evidence registry (strata_pipeline/confidence.py + evidence.py already matched 07 §8 from T1.2; added C3/C4 + multi-rule-binding test coverage)
- [x] T3.7 Exporter + make reproduce (deterministic) — wiring complete; 15_9-F-11_A fully validated live (real bugs found+fixed: hold_last_value, plausible_ranges, frozen_value exclusions, qc_score wiring, DDR-window bounding). Other 5 real wells (15_9-F-1_C/F-15_D/F-14/F-12/F-5) not yet validated live. Root-caused (not just "slow"): each has multi-year gaps between short DDR-coded drilling campaigns (e.g. F-1_C: 1056h of real activity inside a 939-day outer span — the smallest ratio of the 5; F-5 is worst at ~62x), and the pipeline's dense 1s-grid-per-channel design (required by the STRS export's fixed-cadence format, 04_DATA_CONTRACTS.md §4) materializes that whole span per channel. Vectorized ingest/QC/align/rigstate end-to-end with numpy (commits 411fa31, c84ceaa, d7fe24e, 116c9cf) — real, verified ~2-4x speedup and peak-RSS cut roughly in half for F-1_C — but it still doesn't reliably fit in this dev machine's available RAM (16GB, heavily multi-tasked). Closing the rest needs either materially more free RAM or revisiting the STRS dense-grid format for multi-campaign wells (a data-contract change, out of scope for a quick fix) — not further code-level optimization of this same architecture. Revisit on a machine with more headroom, or as its own ADR'd task.
- [x] T8.3 FastAPI service (serves export) — all P0/P1 routes + binary channel endpoint; /copilot/ask returns an honest live_mode_required stub pending T8.4
- [x] T8.4 Copilot agent, tools, verifier (live) — services/api/strata_api/copilot/{tools,agent,verifier,prompts/system.md}; 12 tools from 07 §12 (thin wrappers over the export, pass-through evidence_ids), Anthropic Messages API tool-use loop (model from STRATA_LLM_MODEL, max 12 tool calls, graceful error on budget/parse/LLM failure), submit_answer->CopilotAnswer->verifier->SSE answer event. rigstate_summary mints fresh evidence via a per-session EvidenceRegistry for its arbitrary-window aggregation (ADR 0008) since that's the one tool whose number was never pre-exported. Unit tests: fake-LLM-client agent tests (verified claim, fabricated evidence id, tool-call budget exhausted, tool error recovery) + tools tests + verifier tests (match, rounding tolerance, unit mismatch incl. equivalent-unit match, missing/unknown evidence, stray numbers in text) against the committed fixture export. Added services/api/strata_api to make typecheck/CI (wasn't checked before T8.4).
- [~] T8.5 Recorder + session catalogue — recorder.py (CopilotEvent list -> dt_ms deltas -> JSONL + merged index.json, services/api/strata_api/copilot/recorder.py) and the driver (eval/strata_eval/record_sessions.py, seeded with the one demo question 08_TESTING_AND_ACCEPTANCE.md §3 names literally) are built and unit-tested with a fake LLM client. Not yet run for real: needs ANTHROPIC_API_KEY, not configured in this environment (same kind of external blocker as T3.7's real-well memory limit — code is done, execution is not). Run `python -m strata_eval.record_sessions` with a real key to actually populate `copilot/sessions/` with a live (non-fixture) recording before closing this out.
- [~] T9.2 Eval runners (ablation) — eval/gold/questions.yaml (template only, status=pending, one EXAMPLE- entry documenting the schema, excluded from the >=25 count), eval/strata_eval/{run_ablation.py,score.py}. Four configs (no_tools/simple_rag/full/full_minus_physics) via agent.py's new allowed_tools/extra_context params (physics-tool split recorded in ADR 0008 decision 4); score.py computes Metrics (answer_correctness, numbers_verified_pct, unsupported_numbers, correct_insufficient_pct, median_latency_s) and updates eval.json's ablation+gold_set fields only (qc/rigstate_agreement stay the export pipeline's job). Runs end-to-end on a 3-question smoke set with a fake LLM client (test_run_ablation_smoke.py) — real run is Sergei's gold set authorship + an ANTHROPIC_API_KEY away, same external-blocker pattern as T3.7/T8.5.
- [~] T10.4 Real-data e2e re-run — exported real data for 15_9-F-11_A (the one validated real well; other 5 still blocked, see T3.7) via generate_real, replacing its mock fixture entry (is_mock:false) while the other 8 wells keep theirs. Found and fixed 2 real bugs verifying it: (1) KPI evidence-id collision across conn_s2s/conn_w2w sharing {well,stat} params with no kpi name, silently overwriting each other's registry record; (2) series export's nan_run_gaps had no min-gap threshold, so a real irregularly-sampled channel turned every missing second into its own GapInterval (370k+ for one channel, 425MB index.json) — added the same threshold QC already uses + vectorized it (532MB -> 110MB well export). Updated the handful of web/API tests implicitly coupled to this well being mock. NOT done: e2e demo.spec.ts still hardcodes mock-fixture timestamps/MOCK-badge assumptions and needs the demo.config.json rework the plan calls for (not attempted blind — Playwright's browser binary isn't installed in this environment, so edits couldn't be visually verified); the real export is also ~110MB vs the 25MB/well performance budget (08_TESTING_AND_ACCEPTANCE.md §4), which was calibrated against the much smaller mock fixture — not a bug, but an open product question (shrink the real export's resolution/window, or revisit the budget for real wells) that needs a call, not a unilateral fix.

## M5 P1
- [~] T11.1 Depth-indexed export — `pipeline/strata_pipeline/formation/depth_features.py`: bins the already time-aligned 1 Hz channels onto 1 m MD bins keyed by BITDEPTH (ROP>0 only — see module docstring), mean-aggregating ROP/WOB/RPM/TORQ/GAS per bin, plus MSE (Teale) and dxc (Jorden & Shirley, ECD-corrected) per 07 §9/§11, plus a `rolling_mean_std` helper over an arbitrary window for T11.2's 5/20 m rolling features. Found a real blocker while building it: no Volve archive we downloaded has bit-size/BHA records (docs/DATA_INVENTORY.md), which both MSE and dxc need (bit area / diameter term) — `bit_diameter_in` is a required, never-guessed parameter (ADR 0009); real wells get null MSE/dxc until that data is sourced, mock fixture wells can supply a synthetic value like the rest of their synthetic curves. Not yet wired into `run_well.py` or exported as a static file — no contract for a depth-indexed export file exists in 04_DATA_CONTRACTS.md (the per-well file list doesn't name one), and 07 §9 describes these as classifier *training* features, not a UI-facing artifact, so this is a pipeline-internal module for T11.2 to call, not a new JSON endpoint. Unit-tested against synthetic channels (11 tests, `pipeline/tests/test_depth_features.py`).
- [ ] T11.2 Formation classifier (LOWO) + card + predictions — BLOCKED same as T11.1's MSE/dxc: needs real formation tops for training labels, and none exist in the downloaded Volve archives (docs/DATA_INVENTORY.md §1: "Formation tops were not found as a distinct file type... may be inside the un-downloaded Well_logs*.zip archives, 6.9-7.0GB each"). Revisit after either downloading+parsing those archives for tops, or building this against synthetic mock-fixture tops only (consistent with the rest of the mock-well story) while real wells stay `insufficient_data` for formations — a product call on scope, not a code fix.
- [ ] T11.2 Formation classifier (LOWO) + card + predictions
- [ ] T11.3 S6 Formation screen
- [ ] T11.4 Offset compare
- [ ] T11.5 Depth↔time linking
- [ ] T11.6 Formation brief sessions
- [ ] T12.1 DDR event extraction
- [ ] T12.2 Precursor windows + bands
- [ ] T12.3 S6 event panel
- [ ] T12.4 S7 Issue catalogue
- [ ] T12.5 Events model card
- [ ] T13.1 Replay event export
- [ ] T13.2 Replay transport (timer + WS)
- [ ] T13.3 S2 replay UI + alerts

## M6 P2
- [ ] T14.1 S10 MSE per bit run
- [ ] T14.2 S9 Torque & drag broomstick
- [ ] T14.3 S11 Trip-speed envelope
- [ ] T14.4 full_minus_physics ablation

## Needs Sergei (not agent work)
- [ ] Rig-state gold labels (200 windows) → eval/rigstate_gold.csv
- [ ] Copilot gold question set (≥ 25) → eval/gold/questions.yaml
- [x] TADI paper citation + summary for S5 (written at T9.1 from `docs/references/TADI_PAPER_2605.00060v1.pdf`)
- [ ] OnePetro PDFs of SPE-227235-MS and SPE-229231-MS before public positioning
- [ ] Visual review of each screen against comps
