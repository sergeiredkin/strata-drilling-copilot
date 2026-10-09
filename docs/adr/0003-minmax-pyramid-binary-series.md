# ADR 0003 — Min/max pyramid in binary chunks for time series
Status: accepted (2026-10-09)
Context: 1 Hz × 30+ days × 7 channels; spikes must survive downsampling; no server in static mode.
Decision: L0–L6 levels (×8 bucket growth) storing min and max per bucket in STRS little-endian f32 chunks.
Consequences: ~2 buckets/px drawing budget; small JSON; one decoder shared by static and live mode.
