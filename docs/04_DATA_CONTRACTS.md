# Data contracts

Source of truth: `contracts/schemas/strata.schema.json` (types) and `contracts/endpoints.yaml` (routes and the
static-file mapping). This document explains the rules; it never overrides the schema.

## 1. Global rules
1. **Units.** Everything stored and transmitted is SI-ish as listed in `$defs/Unit` (m, m/h, kN, kN.m, bar, L/min,
   rpm, sg, MPa). The UI converts on display only. Oilfield mapping lives in `apps/web/src/units/registry.ts`:
   m→ft ×3.28084 · kN→klbf ×0.224809 · kN.m→kft.lbf ×0.737562 · bar→psi ×14.5038 · m/h→ft/h ×3.28084 ·
   L/min→gpm ×0.264172 · sg→ppg ×8.34540 · MPa→psi ×145.038.
2. **Time** is epoch milliseconds UTC. Depth is metres MD unless a field says TVD.
3. **Every computed number is a `Quantity`** `{value, unit, evidence_id, precision?}`. Raw sensor arrays and
   interval boundaries are not Quantities; anything aggregated, derived or counted-and-displayed is.
4. **Nulls, not zeros.** Unknown or not-computable values are `null`; the UI shows `—` with a tooltip saying why.
5. **Confidence** `{level, reason, rule_ids}` is produced only by `pipeline/confidence.py`.
6. **Mock flag.** `WellSummary.is_mock = true` for fixtures. The app shows a MOCK badge on any screen that renders
   a mock well, and the e2e test asserts the badge disappears once real exports are used.
7. **Versioning.** Bump `version` in `endpoints.yaml` and schema `title` on breaking changes; regenerate.

## 2. Code generation (Phase 1)
- TS types: `json-schema-to-typescript` → `apps/web/src/contracts/types.ts`.
- zod: `json-schema-to-zod` → `apps/web/src/contracts/zod.ts` (dev-mode validation of every response).
- Pydantic v2: `datamodel-code-generator --input-file-type jsonschema` → `pipeline/strata_pipeline/contracts.py`
  and re-exported in `services/api`.
- CI check `make contracts-check` fails if regenerated output differs from committed files.

## 3. Static export layout (`apps/web/public/data/`)
```
wells.json
repro.json
eval.json
issues.json
reconciliation/all.json, reconciliation/{well}.json
models/formation_card.json, models/events_card.json
evidence/shards.json + evidence/{00..ff}.json     # shard by first 2 hex chars after "ev_"
copilot/sessions/index.json + copilot/sessions/{id}.jsonl
issues/{issue}_precursors.json
wells/{id}/
  sections.json  depthtime.json  rigstate.json  ddr.json  mismatches.json
  kpis.json  ilt.json  formations.json  formation_pred.json  replay_events.json
  series/index.json
  series/{CH}/L{n}/{chunk}.bin
```

## 4. Binary series block (`STRS`)
Little-endian. Header 24 bytes: `u32 magic=0x53525453 ('STRS')`, `u32 n`, `f64 t0_ms`, `f32 bucket_s`,
`u32 reserved`. Body: `f32[n] min`, `f32[n] max`. Bucket i covers `[t0 + i·bucket, t0 + (i+1)·bucket)`.
`NaN` marks no data; gaps are also listed explicitly in `series/index.json`. At L0 (1 s) min == max.

## 5. Copilot session file (`.jsonl`)
One `CopilotEvent` per line, in order, each with `dt_ms` since previous event. Last line is `answer` or
`error`. StaticSource replays with the recorded delays (capped at 1500 ms per step).

## 6. Evidence
`Evidence.sources[]` lists every file (with sha256) the number was computed from, the channels and time/depth
window. The provenance popover shows: tool, params, sources, window, value in SI and in the current unit
system, verification state, and a "show window in Workspace" deep link.
