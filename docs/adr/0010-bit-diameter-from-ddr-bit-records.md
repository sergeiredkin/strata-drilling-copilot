# ADR 0010 — Bit diameter resolved from DDR `<bitRecord>`, per depth interval

Status: accepted (2026-10-13) — resolves the blocker ADR 0009 recorded.

Context: ADR 0009 found no dedicated bit-size/BHA-record file in the downloaded Volve archives
and made `bit_diameter_in` a never-guessed, caller-supplied scalar that's `None` (all-NaN MSE/dxc)
for real wells. Re-checking the Daily Drilling Report XML itself (not a separate archive) found
it does carry real bit data: `<drillReport><bitRecord><diaBit uom="in">...</diaBit>...<bitRun>
<mdHoleStart>...</mdHoleStart><mdHoleStop>...</mdHoleStop>...</bitRun></bitRecord>`, a sibling of
the `<activity>` rows `ingest/ddr.py` already parses, present on whichever day's report records a
bit change (confirmed for all 6 modelled wells — e.g. 15/9-F-11 A: 8.5 in bit, 2586-3762 m;
15/9-F-5: 17.5/12.25/8.5 in across its hole sections). Per Sergei's explicit instruction: the bit
diameter for a given depth is the hole size it's cutting — the same number, not a separate lookup.

Decision: `ingest/ddr.py` gained `parse_bit_runs`/`load_well_bit_runs`, returning one row per
`<bitRun>` with `diameter_in`/`md_top`/`md_base`/`report_date`. Rows with a missing diameter, a
non-inch `uom`, or a missing/degenerate MD range are dropped, never guessed (one malformed F-12
entry — `mdHoleStop` absent — is dropped this way, confirmed by inspection).
`formation/depth_features.py`'s `BitInterval`/`bit_diameter_by_md` resolve each 1 m MD bin's
diameter by matching it against these reported `[md_top, md_base)` ranges; a bin outside every
interval still gets NaN (e.g. the real F-11 A well has bit coverage from ~2480-3770 m MD but no
record at all above 2480 m, since no bit change was reported there within the ingested drilling
window) — the "never guessed" rule from ADR 0009 is unchanged, just narrower in scope now that
real data covers most of the well.

Real-data quirk recorded for whoever touches this next: F-11 A's two bit records overlap in a way
that isn't simple depth order — a 2013-05-25 report gives 8.5 in for 2586-3762 m, and a *later*
2013-05-29 report gives 12.25 in for 2585-2787 m (a larger bit, shallower range, reported after
the smaller/deeper one — inconsistent with normal top-down hole-size reduction, likely a report
correction or data-entry quirk in the public archive, not re-verifiable from what's downloaded).
`bit_diameter_by_md` resolves overlaps by **intervals-list order, last wins** — callers must pass
`load_well_bit_runs`' rows in their returned (chronological/file) order so a later report revising
an earlier one takes precedence, which is the simplest defensible rule without second-guessing the
source archive. Verified end-to-end against the real F-11 A well (see commit introducing this
ADR): 1177 of 1291 populated MD bins get a finite MSE; `dxc` stays all-NaN for this well because
it has no ECD channel ingested at all (a separate, already-honest null, unaffected by this ADR).
