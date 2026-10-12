# `rigstate_gold.csv` — pending hand-labelling

Status: **pending** (per `contracts/schemas/strata.schema.json`'s `EvalReport.gold_set.status`
enum) — this file is currently header-only. `docs/07_DATA_AND_ALGORITHMS.md` §4 validation step
(b) calls for "a hand-labelled gold sample of 200 random 10-min windows ... labelled by Sergei" —
the agent does not fabricate these labels (CLAUDE.md: never fabricate data; unknown values stay a
visible placeholder, not a guess).

## Format

```
well,t0,t1,label,notes
15_9-F-11_A,2013-05-15T08:00:00+00:00,2013-05-15T08:10:00+00:00,rotary_drilling,
```

- `well`: well id matching the pipeline's well identifiers.
- `t0`, `t1`: window bounds, ISO-8601 with a UTC offset (10 minutes apart per the spec).
- `label`: one of `strata_pipeline.rigstate.rules.STATES` — the human-judged true rig state for
  that window.
- `notes`: optional free text (e.g. "ambiguous — right at a connection boundary").

## How to fill it in

1. Pick 200 random 10-minute windows across the wells with real time-log coverage
   (`docs/DATA_INVENTORY.md`).
2. For each, look at the raw curves (HKLD, BPOS, RPM, FLOWIN, BITDEPTH, HOLEDEPTH) around that
   window and judge the dominant rig state by eye.
3. Append a row. Once filled, flip `EvalReport.gold_set.status` from `pending` to `draft`/`final`
   at export time (T3.7/eval wiring).

## Using it once filled

`eval/strata_eval/rigstate_agreement.py`'s `load_gold()` + `compute_agreement()` turn this file
plus a well's classifier output (`strata_pipeline.rigstate.classify.run_rigstate`) into per-state
precision/recall and per-well agreement, matching `EvalReport.rigstate_agreement`'s shape. The
agreement script itself is already implemented and unit-tested against a synthetic gold set
(`eval/tests/test_rigstate_agreement.py`) — only the real labels are missing.
