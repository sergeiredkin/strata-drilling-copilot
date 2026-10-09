# STRATA — Drilling Copilot (open demo)

Drilling analytics and an evidence-grounded AI copilot built on public data (Equinor Volve, Utah FORGE).
It reconstructs rig operations from surface sensor data, measures lost time the daily reports don't show,
and answers questions with numbers that are traceable to their source — or says "insufficient data".

Status: **planning complete, implementation not started.** Start with `CLAUDE.md` and `docs/02_IMPLEMENTATION_PLAN.md`.

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
