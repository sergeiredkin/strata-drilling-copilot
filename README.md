# STRATA — Drilling Copilot (open demo)

Drilling analytics and an evidence-grounded AI copilot built on public data (Equinor Volve, Utah FORGE).
It reconstructs rig operations from surface sensor data, measures lost time the daily reports don't show,
and answers questions with numbers that are traceable to their source — or says "insufficient data".

**Live demo (static mode, fixtures):** https://sergeiredkin.github.io/strata-drilling-copilot/

## Status

Implementation in progress, critical path through Phase 3 and T8.3 done:
- **M0–M3**: monorepo, contracts, fixtures, trust kit, workspace (S1/S2), performance + copilot UI (S3/S4,
  static sessions), trust screen (S5), Playwright demo-script e2e, a11y + copy lint.
- **Phase 2/3 (real data)**: Volve WITSML + DDR ingest, QC, rig-state classifier, KPIs, invisible lost time,
  DDR reconciliation, confidence/evidence, and the exporter — live-validated end to end against the real
  downloaded Equinor Volve archive for one well (`15_9-F-11_A`); see `tasks/BACKLOG.md` for the other wells'
  status and a few real-data bugs found and fixed along the way.
- **T8.3**: FastAPI live-mode service serving the same export the static build reads, with contract tests.
- **Not started yet**: the copilot's LLM tool-use agent/verifier (T8.4), session recorder (T8.5), and the
  formation/events models (P1, later phases). `/copilot/ask` currently returns an honest
  "not implemented yet" response rather than a fake one.

Start with `CLAUDE.md` and `docs/02_IMPLEMENTATION_PLAN.md`; `tasks/BACKLOG.md` has the current task-by-task
checklist.

## Running it

```
make setup      # pnpm install + uv sync
make fixtures   # generate mock fixtures into apps/web/public/data
make web        # vite dev server, static mode — http://localhost:5173
```

No backend or API key needed for the demo above. For live mode against the real pipeline:

```
make pipeline WELL=15_9-F-11_A   # ingest -> qc -> rigstate -> kpis -> export, one real well
make api                          # FastAPI on :8000, serves data/export
```

`make pipeline` needs the raw Volve archive downloaded locally first (not included in this repo — see
`docs/LICENSES.md` for how it was obtained and what the licence permits).

| Doc | Purpose |
|---|---|
| `docs/01_PRODUCT_SPEC.md` | Product spec v0.2 (screens, requirements, non-goals, proposals PR-1…PR-6) |
| `docs/02_IMPLEMENTATION_PLAN.md` | Phased, task-level implementation plan for the coding agent |
| `docs/03_ARCHITECTURE.md` | Repo layout, front-end/back-end architecture, data flow, static vs live mode |
| `docs/04_DATA_CONTRACTS.md` + `contracts/schemas/` | Endpoints and JSON Schemas (source of truth) |
| `docs/05_DESIGN_SYSTEM.md` | Tokens, rig-state palette, components, copy rules |
| `docs/06_SCREENS.md` | Per-screen specs S1–S11 and the function → page map |
| `docs/07_DATA_AND_ALGORITHMS.md` | Data sources, ingestion, QC, rig state, KPIs, ILT, reconciliation, models, physics |
| `docs/08_TESTING_AND_ACCEPTANCE.md` | Test strategy, performance budgets, demo-script acceptance test |
| `docs/09_INDUSTRY_REVIEW.md` | Review of SPE-227235-MS / SPE-229231-MS and STRATA positioning |
| `docs/design/` | Design comps exported from the STRATA canvas |
| `tasks/BACKLOG.md` | Task checklist |
