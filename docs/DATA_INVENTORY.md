# Data inventory (T2.1)

Confirms what `docs/07_DATA_AND_ALGORITHMS.md` §1 asked T2.1 to verify: folder structure, which
wellbores have time-indexed logs, timestamp time zone, and licence terms (licence terms are in
`docs/LICENSES.md`; this file is the per-wellbore coverage table). Raw files live in
`data/raw/equinor_volve/` (gitignored); `data/raw/MANIFEST.json` has sha256/byte counts for the
source archives.

## 1. Equinor Volve — access

Downloaded 2026-10-12 via the Equinor listing in **Databricks Marketplace** (see
`docs/LICENSES.md` §3 for the exact steps — the old direct-download "Volve Data Village" page is
retired; this is now the only path, and it's a manual authenticated click-through, not a
scriptable URL). Three archives downloaded (full sha256 in `data/raw/MANIFEST.json`):
`Volve_WITSML Realtime drilling data.zip` (2.3 GB), `Volve_Reports.zip` (162 MB),
`Volve_Well_technical_data.zip` (212 MB). Selectively extracted to
`data/raw/equinor_volve/{witsml,reports,well_technical_data}/` for the 6 wells below (full
extraction of the WITSML archive alone would be ~36 GB for all ~31 wellbores in it; not done).

**Structure surprises, recorded so T2.2/T2.3 don't have to rediscover them:**
- The WITSML archive registers the *same physical wellbore* under multiple top-level folders
  named `<country>-<operator>-<well>` (e.g. `NA-NA-15_$47$_9-F-5`, `Norway-StatoilHydro-15_$47$
  _9-F-5`, `Norway-Statoil-NO 15_$47$_9-F-5`) — Statoil's own operator name changed over the
  field's life (Statoil → StatoilHydro → Statoil → Equinor) and each re-registration got its own
  folder. **Ingest must union across all variant-prefix folders for a given well**, not just the
  most-recent-looking one — our F-14 and F-5 both have real log data split across 2-3 prefix
  variants.
- `$47$` in folder/file names is an HTML-entity-style escape for `/` (so
  `15_$47$_9-F-11` = `15/9-F-11`).
- A well's numbered wellbore subfolder (`.../NO 15_$47$_9-F-15/1/`, `.../2/`, ...) does **not**
  reliably correspond to the public NPD suffix letter by position — e.g. under the `F-15` well
  folder, index `1` is actually wellbore `F-15 C` and index `2` is `F-15 D`. The real name is only
  recoverable from the `_wellboreInfo/*.xml` file inside each numbered folder
  (`<nameWellbore>` field). **Never assume index order maps to A/B/C/D.**
  "F-11 A" was found at `Norway-Statoil-NO 15_$47$_9-F-11/4/`, not `/1/`.
- Within one wellbore, "time-indexed logs" are not one clean composite feed — they're dozens of
  separate named log objects (service-company/tool-specific: `GenTime`, `Hydraulics`,
  `TripTime`, `Connection`, per-hole-section `"... - Time Log"` names, etc.), each with its own
  `logCurveInfo` mnemonic list and its own date range. Drilling parameters (HKLD, WOB, RPM,
  TORQUE/TORQ, SPPA/SPP, FLOWIN/FLOWOUT, BPOS, DMEA/DBTM) are scattered across several of these
  per well, not confined to one. **Ingest needs a per-well scan + merge, not a fixed log-name
  lookup** (confirmed by scanning all extracted logs for drilling-keyword mnemonics — see
  commit history for the scan script).
- Sampling cadence within a single log is **irregular**, not a fixed Hz — observed gaps in one
  F-11 A log alternate between ~30-36 s and ~1-3 s within the same curve. This matches known
  characteristics of the public Volve WITSML dump (MWD/memory-dump-style logging, not a uniform
  EDR feed) and means QC's gap/frozen-value handling (`07_DATA_AND_ALGORITHMS.md` §3) will see
  real, non-synthetic gap patterns.
- **Time zone differs by file type**: real-time WITSML log timestamps are UTC (`Z` suffix,
  `dateTimeIndex`/`startDateTimeIndex`). Daily Drilling Report XML timestamps
  (`witsml:dTimStart` etc.) are **Norway local time** (`+01:00`/`+02:00`, i.e. CET/CEST) —
  ingest must convert DDR timestamps to UTC before aligning with the real-time logs.
- Formation tops were **not** found as a distinct file type in what we downloaded — `Reports.zip`
  contains only a Discovery report and the PUD (field-level, not per-well tops), and
  `Well_technical_data.zip` has no tops-specific folder. May be inside the un-downloaded
  `Well_logs*.zip` archives (6.9-7.0 GB each, skipped — see `data/raw/MANIFEST.json`); revisit if
  S6/Formation (T11.x, P1) needs real tops before then.

## 2. Per-wellbore coverage (the 6 wells STRATA's fixtures currently model)

Coverage kinds per `docs/04_DATA_CONTRACTS.md`'s 6: `time_logs`, `depth_logs`, `daily_reports`,
`formation_tops`, `survey`, `mud`.

| Well (STRATA id) | WITSML real-time (`time_logs`) | DDR (`daily_reports`) | Survey | Formation tops | Mud |
|---|---|---|---|---|---|
| 15/9-F-11 A (`15_9-F-11_A`) | ✅ `Norway-Statoil-NO 15_$47$_9-F-11/4/`, 43 time-indexed logs, UTC, range 2013-05-13 .. 2015-09-22 (drilling-era: ~2013-05-13 .. 05-29) | ✅ 14 reports, 2013-05-15 .. 2013-05-29, local-time XML | ✅ `WellWellbore/15_9-F-11/15_9-F-11 A/` — Standard Survey Report PDF + raw survey export | ❌ not in downloaded archives | ❌ not in downloaded archives |
| 15/9-F-1 C (`15_9-F-1_C`) | ✅ `Norway-Statoil-NO 15_$47$_9-F-1 C/2/`, 54 logs, UTC, range 2014-02-19 .. 2016-09-18 | ✅ 98 reports, 2014-02-22 .. 2016-10-22 | ✅ `WellWellbore/15_9-F-1/15_9-F-1 C/` | ❌ | ❌ |
| 15/9-F-15 D (`15_9-F-15_D`) | ✅ `Norway-Statoil-NO 15_$47$_9-F-15/2/`, 49 logs, UTC, range 2013-11-09 .. 2016-09-16 | ✅ 99 reports, 2013-11-11 .. 2016-10-19 | ✅ `WellWellbore/15_9-F-15/15_9-F-15 D/` | ❌ | ❌ |
| 15/9-F-14 (`15_9-F-14`) | ✅ 2 registrations to union — `Norway-Statoil-NO 15_$47$_9-F-14/1/` (10 logs, 2015-09-22 .. 2016-09-14) + `Norway-StatoilHydro-15_$47$_9-F-14/1/` "Main Wellbore" (7 logs, 2007-11-04 .. 2015-09-22) | ✅ 134 reports, 2007-11-06 .. 2016-10-20 | ✅ `WellWellbore/15_9-F-14/15_9-F-14/` | ❌ | ❌ |
| 15/9-F-12 (`15_9-F-12`) | ✅ 2 registrations — `Norway-Statoil-15_$47$_9-F-12/1/` "Main Wellbore" (12 logs, 2007-06-13 .. 2015-09-22) + `Norway-Statoil-NO 15_$47$_9-F-12/1/` (10 logs, 2015-09-22 .. 2016-08-27) | ✅ 165 reports, 2007-06-14 .. 2016-10-21 | ✅ `WellWellbore/15_9-F-12/15_9-F-12/` | ❌ | ❌ |
| 15/9-F-5 (`15_9-F-5`) | ✅ 3 registrations — `NA-NA-15_$47$_9-F-5/1/` "Main Wellbore" (7 logs, 2007-11-15 .. 2015-09-22) + `Norway-Statoil-NO 15_$47$_9-F-5/1/` (10 logs, 2015-09-22 .. 2016-09-11) + `Norway-StatoilHydro-15_$47$_9-F-5/1/` "Main Wellbore" | ✅ 103 reports, 2007-11-15 .. 2016-10-17 | ✅ `WellWellbore/15_9-F-5/15_9-F-5/` | ❌ | ❌ |

Note: the date ranges above span each wellbore's *entire recorded history on the WITSML/DDR
server*, which for several wells extends years past their actual drilling campaign (Volve
produced until 2016; reports/logs keep accumulating against the same wellbore ID through
production, workovers, etc.). The real *drilling* window per well is narrower and will be
derived in T2.2/T2.3 from rig-state activity, not assumed from the full file date range.

## 3. Wells available but not yet in STRATA's fixture roster

The archives have DDR + real-time WITSML coverage for roughly a dozen more Volve wellbores beyond
the 6 above: **F-1, F-1 A, F-1 B, F-4, F-7, F-9, F-9 A, F-10, F-11 (base + B + T2), F-15 (base +
A + B + C)**. Not pulled in yet — expanding the fixture/well roster is a product decision (which
wells, how many, matching S1's comp design), not just a data-availability question. Flagged here
for a deliberate follow-up rather than auto-expanding.

## 4. Utah FORGE

**Blocked on infrastructure, not licence** (CC BY 4.0, confirmed open) — see `docs/LICENSES.md`
§2 and `data/raw/MANIFEST.json`'s `forge` field for the current outage details. No files
downloaded yet.
