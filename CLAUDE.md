# CLAUDE.md — STRATA Drilling Copilot (instructions for the coding agent)

You are implementing **STRATA**, an open, reproducible drilling-analytics demo with an evidence-grounded AI copilot,
built only on public data (Equinor Volve, Utah FORGE). Read this file fully before every session.

## 1. Read order (mandatory before writing code)
1. `docs/02_IMPLEMENTATION_PLAN.md` — the implementation plan (ICA). Work strictly task by task, in the order given.
2. `tasks/BACKLOG.md` — the checklist. Tick tasks here as you finish them.
3. `docs/01_PRODUCT_SPEC.md` — what the product must do and must NOT do.
4. `docs/03_ARCHITECTURE.md` and `docs/04_DATA_CONTRACTS.md` — before touching data or APIs.
5. `docs/05_DESIGN_SYSTEM.md` and `docs/06_SCREENS.md` — before touching any UI.
6. `docs/07_DATA_AND_ALGORITHMS.md` — before touching the pipeline (rig state, KPIs, ILT, models).
7. `docs/08_TESTING_AND_ACCEPTANCE.md` — definition of done.
8. `docs/design/rendered/*.html` (open in a browser — pixel reference) and `docs/design/comps/*.dc.html`
   (exact styles and mock-data shapes). See `docs/design/README.md`. Never copy them into `apps/web`.

## 2. Non-negotiable product rules
- **Trust over polish.** Every computed number shown anywhere is a `{value, unit, evidence_id}` and renders through
  the `<Num>` component with provenance. A number without evidence is a bug.
- **Gaps are never interpolated.** Missing data is drawn hatched. Series values inside gaps are `null`.
- **Confidence is computed only by the backend/pipeline.** The front end renders `{level, reason}` and never derives it.
- **Advisory only.** No setpoints, no "autopilot", no "recommended WOB/RPM", no "% NPT reduction" claims,
  no fleet-scale claims, no claims about any vendor product. Copy-lint list: `docs/05_DESIGN_SYSTEM.md#copy-lint`.
- **Static mode first.** The app must run from a fresh clone with no backend and no API key, reading exported
  files from `apps/web/public/data/`. Live mode only switches on when `VITE_API_URL` is set.
- **Mock data is labelled.** Until real exports replace fixtures, every screen shows a visible `MOCK` badge.
- **Contracts are the source of truth.** Change `contracts/schemas/*.json` first, regenerate types, then code.
  Never hand-edit generated files.

## 3. Working agreement (two-instance setup)
- This repo is implemented by you (Claude Code in VS Code). Planning/review happens in a separate chat.
- **Do not `git push`, add remotes, rewrite history or force anything.** Sergei reviews and pushes.
- You MAY make local commits, one per task, with the message format `T<id>: <short summary>`.
- One task ID per change set. Start each summary with the task ID, e.g. `T6.2 — TrackStack cursor sync`.
- If a task is ambiguous, prefer the spec; if the spec is silent, choose the simplest option, record it
  as a short ADR in `docs/adr/`, and continue. Do not stop to ask unless the choice is irreversible.
- Never fabricate data, metrics, citations or file paths. Unknown values are `null` + a visible placeholder.

## 4. Commands (target state after Phase 0)
```
make setup        # pnpm install + uv sync
make contracts    # regenerate TS types, zod, Pydantic from contracts/schemas
make fixtures     # generate mock fixtures into apps/web/public/data (validated)
make web          # vite dev server (static mode)
make api          # FastAPI on :8000 (live mode)
make pipeline WELL=<id>   # ingest -> qc -> rigstate -> kpis -> export for one well
make export       # full export for all wells into apps/web/public/data
make test         # pytest + vitest
make e2e          # Playwright demo-script test in static mode
make reproduce WELL=<id>  # regenerate every number for a well; prints manifest
```

## 5. Stack (fixed — do not substitute without an ADR)
Web: React 18 + TypeScript (strict) + Vite, uPlot (dense synchronized tracks), ECharts (statistics),
TanStack Query, Zustand, Tailwind with CSS-variable tokens, zod, Vitest, Playwright, pnpm.
Python ≥3.11: uv, Pydantic v2, polars + pyarrow, numpy, scikit-learn, FastAPI + sse-starlette, pytest.
LLM: Anthropic API via the official Python SDK; model id from env `STRATA_LLM_MODEL`.

## 6. Definition of done for any task
Acceptance criteria in the plan are met · types regenerated if contracts changed · tests added and passing ·
no TypeScript `any` in new code · no console errors · static mode still works · BACKLOG ticked.
