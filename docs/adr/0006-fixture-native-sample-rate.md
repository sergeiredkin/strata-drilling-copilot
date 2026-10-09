# ADR 0006 — Fixture generator covers fewer days at true 1 Hz, not literal 30
Status: accepted (2026-10-09)

Context: T1.2 (`02_IMPLEMENTATION_PLAN.md`) asks for a 30-day, 1 Hz fixture for `15_9-F-11_A`. The STRS
pyramid's bucket sizes (L0=1 s, L1=8 s, … per `03_ARCHITECTURE.md` §3.4) are fixed global constants, not
derived from a channel's native rate, so sampling coarser than 1 Hz would leave most L0 buckets genuinely
empty (indistinguishable from a real gap) rather than just "lower resolution". Changing the native rate is
therefore not a safe way to shrink fixture volume; 1 Hz × 30 days × ~9 channels (~2.6M samples/channel) is
still the right shape to exercise the pyramid, but is slow to synthesize and large to keep in git for data
whose only job is to drive the UI/pipeline, not to be a realistic 30-day record.

Decision: fixtures keep true 1 Hz native sampling (`04_DATA_CONTRACTS.md` §4/§1 bucket semantics unchanged),
but each well's dense time-log span is shorter than its nominal well life: `15_9-F-11_A` gets 4 days of
contiguous 1 Hz data (with the one 4-min/day gap and slow connections still present), `15_9-F-5` gets 2 sparser
days, the FORGE well `16A_78-32` gets 2 days. Section/DDR/KPI/ILT records still span the well's full nominal
duration (`years`, section date ranges) — only the dense series payload is windowed — so S1's "30 days" framing
and multi-section structure are intact; S2's zoom-from-full-well-to-one-connection and S3's day/section
breakdowns still have real data to show, just over a shorter dense window.

Consequences: fixture repo size and `make fixtures` runtime stay small (~hundreds of thousands, not millions,
of samples/channel); L0 bucket width stays a true 1 s, so gap-hatching and the pyramid decoder are exercised
exactly as real Volve/FORGE exports (Phase 2+) will exercise them — only the covered time range shrinks. T10.4
(real-data re-run) replaces this with the true multi-week export.
