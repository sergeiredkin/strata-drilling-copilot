# ADR 0006 — Fixture generator uses 0.1 Hz native sampling, not literal 1 Hz
Status: accepted (2026-10-09)

Context: T1.2 (`02_IMPLEMENTATION_PLAN.md`) asks for a 30-day, 1 Hz fixture for `15_9-F-11_A` to mirror the
richest Volve well. Literal 1 Hz × 30 days × ~9 channels is ~2.6M samples/channel/well; across L0 STRS chunks
(6 h each, min+max f32) that is tens of MB per channel and a correspondingly slow generation pass, for fixture
data whose only job is to exercise the UI/pipeline shapes, not to be realistic at sample level.

Decision: the fixture synthesizer (`pipeline/strata_pipeline/fixtures/synth.py`) generates at a native
10 s cadence (0.1 Hz) and declares that as the channel's real sampling interval in `series/index.json` — L0
bucket size shrinks accordingly so the pyramid, gap-hatching, zoom and cursor-sync mechanics are exercised
identically to 1 Hz; only the absolute sample count shrinks (~260k/channel/well instead of 2.6M). Real Volve/
FORGE ingestion (Phase 2) uses the source data's actual rate, which may well be close to 1 Hz; this ADR is
fixture-only and does not change `04_DATA_CONTRACTS.md` or the STRS format.

Consequences: fixture repo size and `make fixtures` runtime stay small; demo zoom/pan still goes from
full-well to single-connection since bucket levels are still defined by the L0 cadence, just coarser;
when real exports replace fixtures (T10.4) the true 1 Hz rate is used and this ADR no longer applies.
