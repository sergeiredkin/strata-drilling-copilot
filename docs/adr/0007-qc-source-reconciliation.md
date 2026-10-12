# ADR 0007 — QC picks one source log per channel by richest coverage, not a merge

Status: accepted (2026-10-12)

Context: `docs/07_DATA_AND_ALGORITHMS.md` §2 defines `time.parquet` as `t_ms` + one column per
canonical channel (wide, single series per channel), but T2.2's ingest (`witsml_time.py`)
deliberately stays long-format — `(t, channel, value, raw_mnemonic, raw_unit, source_log)` — since
a wellbore's real-time data is spread across dozens of separate named WITSML log objects
(`docs/DATA_INVENTORY.md`), and the same canonical channel (e.g. RPM) can appear in several of
them with disagreeing values. Something has to pick the one series each channel's `time.parquet`
column actually holds, and §3 (QC) doesn't say how. The spec is silent, so per CLAUDE.md §3 this
records the simplest defensible choice rather than blocking on it.

Decision: for each canonical channel, QC reconciliation (`pipeline/strata_pipeline/qc/reconcile.py`)
counts raw samples per `source_log` across the whole well and keeps only the source log with the
most samples for that channel; all other source logs' rows for that channel are dropped before the
rest of QC (sentinels/spikes/frozen/resample) runs. Ties break on `source_log` string order, so the
choice is deterministic and reproducible (`make reproduce`). The dropped-source counts are recorded
in the QC report so a reviewer can see what was discarded, rather than silently merging conflicting
readings.

Consequences: a channel reported by a thin secondary log (e.g. a tool that only sampled briefly)
loses that data even where it might have filled a gap in the primary log — acceptable for v1 since
Volve's archive practice is one log genuinely owning each drilling parameter end-to-end, with the
others being partial/duplicate instrumentation (`docs/DATA_INVENTORY.md`). If real data later shows
genuine complementary (non-overlapping-in-time) coverage across logs worth merging, revisit this
ADR before changing the rule — don't silently start interpolating across sources.
