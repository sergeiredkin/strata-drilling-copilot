# ADR 0009 — Bit diameter in T11.1's depth-indexed features: parameter, never guessed

Status: accepted (2026-10-13)

Context: `docs/07_DATA_AND_ALGORITHMS.md` §9/§11 need MSE (Teale) and the corrected d-exponent
(`dxc`, Jorden & Shirley) per 1 m MD bin. Both formulas divide by the bit's cross-sectional area
or raw diameter. None of the downloaded Volve archives contain BHA/bit-run records or a
casing/hole-size schedule (`docs/DATA_INVENTORY.md` §1, also noted at
`pipeline/strata_pipeline/export/real_well.py`'s `build_sections_json` docstring) — there is no
real per-well bit size to read for any of the 6 Volve wellbores STRATA currently models.

Decision: `bin_channels_by_depth`/`compute_mse`/`compute_dxc`
(`pipeline/strata_pipeline/formation/depth_features.py`) take `bit_diameter_in: float | None` as
an explicit caller-supplied parameter, never inferred from the data. `None` (the only honest value
for a real well today) makes `MSE`/`dxc` all-NaN for that well — not a guessed average hole size,
which would be exactly the kind of fabricated number `CLAUDE.md` §2 forbids, silently wrong by
whatever the actual bit-size changes over the well's several hole sections were. Everything else
in `DepthFeatureTable` (ROP, WOB, RPM, torque, gas, per-bin sample count) has no such dependency
and is populated unconditionally.

For mock fixture wells, a synthetic `bit_diameter_in` is exactly as legitimate as the rest of
their synthetic channel curves (same `is_mock: true` labelling as every other fixture number) —
this ADR only constrains what happens for real-data wells.

Consequence for T11.2 (formation classifier): MSE/dxc being null for every real well until bit
records are sourced removes two of the ten listed training features for those wells. The
classifier itself must treat missing features as missing (not zero-fill), the same "nulls, not
interpolated" rule as everywhere else — left to T11.2 to implement against whatever sklearn
pipeline it builds (`HistGradientBoostingClassifier` natively handles NaN features).
