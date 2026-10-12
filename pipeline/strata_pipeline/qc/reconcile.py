"""Picks one `source_log` per channel before per-channel QC runs — see
docs/adr/0007-qc-source-reconciliation.md for why (a wellbore's canonical channel can appear in
several WITSML log objects at once; `time.parquet` needs exactly one series per channel)."""

from __future__ import annotations

import polars as pl


def pick_source_per_channel(long_df: pl.DataFrame) -> tuple[pl.DataFrame, dict[str, dict[str, int]]]:
    """`long_df` has columns `t, channel, value, raw_mnemonic, raw_unit, source_log`. Returns the
    rows restricted to each channel's richest `source_log` (most samples; ties broken by
    `source_log` string order for determinism), plus a per-channel report of every candidate
    source's sample count (so a reviewer can see what was discarded)."""
    if long_df.is_empty():
        return long_df, {}
    counts = (
        long_df.group_by(["channel", "source_log"])
        .len()
        .sort(["channel", "source_log"])
    )
    report: dict[str, dict[str, int]] = {}
    chosen: dict[str, str] = {}
    for row in counts.iter_rows(named=True):
        channel, source_log, n = row["channel"], row["source_log"], row["len"]
        report.setdefault(channel, {})[source_log] = n
        current = chosen.get(channel)
        if current is None or n > report[channel][current]:
            chosen[channel] = source_log
    keep_mask = pl.Series([chosen.get(c) == s for c, s in zip(long_df["channel"], long_df["source_log"], strict=True)])
    return long_df.filter(keep_mask), report
