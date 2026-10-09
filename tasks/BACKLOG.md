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
- [ ] T6.4 Ribbon, DDR lane, mismatches + popover
- [ ] T6.5 S2 assembly

## M2 Performance & Copilot (static)
- [ ] T7.1 S3 KPI cards, distributions, waterfall, by section/day
- [ ] T7.2 S3 Booked-vs-measured, ILT definition, Reproduce (PR-1, PR-2)
- [ ] T8.1 Copilot dock + AnswerCard + trace (static sessions)
- [ ] T8.2 Copilot context plumbing

## M3 Trust + P0 e2e
- [ ] T9.1 S5 Trust (incl. reconciliation matrix, model cards, positioning)
- [ ] T10.1 Playwright demo-script e2e
- [ ] T10.2 Performance budget test
- [ ] T10.3 A11y + copy lint

## M4 Real data (Lane B)
- [ ] T2.1 Data inventory + licences  ← report to Sergei before continuing
- [ ] T2.2 Volve time-log ingest
- [ ] T2.3 Volve DDR ingest
- [ ] T2.4 FORGE ingest
- [ ] T3.1 QC
- [ ] T3.2 Rig-state classifier + gold-sample agreement
- [ ] T3.3 KPIs + composite best
- [ ] T3.4 ILT
- [ ] T3.5 Reconciliation + mismatches
- [ ] T3.6 Confidence module + evidence registry
- [ ] T3.7 Exporter + make reproduce (deterministic)
- [ ] T8.3 FastAPI service (serves export)
- [ ] T8.4 Copilot agent, tools, verifier (live)
- [ ] T8.5 Recorder + session catalogue
- [ ] T9.2 Eval runners (ablation)
- [ ] T10.4 Real-data e2e re-run

## M5 P1
- [ ] T11.1 Depth-indexed export
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
- [ ] TADI paper citation + summary for S5 (PDF received: `docs/references/TADI_PAPER_2605.00060v1.pdf` — summary/citation text still needed at T9.1)
- [ ] OnePetro PDFs of SPE-227235-MS and SPE-229231-MS before public positioning
- [ ] Visual review of each screen against comps
