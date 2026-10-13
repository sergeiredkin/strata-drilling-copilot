# ADR 0008 — Copilot tool signatures and evidence minting for derived numbers

Status: accepted (2026-10-13)

Context: `docs/07_DATA_AND_ALGORITHMS.md` §12 names the copilot tools (`kpi_connection_times(well,
section, stat)`, `kpi_trips(well, section, direction, hole)`, `rigstate_summary(well, t0, t1)`,
etc.) but doesn't give full parameter types or return shapes, and two things are genuinely
ambiguous enough to need a recorded choice rather than a guess re-litigated later.

Decision 1 — `stat` in `kpi_connection_times`: `kpi_trips` has two independent axes (`direction`,
`hole`) because there are four trip KPIs (`trip_{in,out}_{cased,open}`); connections only have two
KPIs (`conn_s2s`, `conn_w2w`), so `stat` is that one axis (`"s2s" | "w2w"`), not a statistic name —
both tools return the *same shape* for symmetry: the full `Distribution` (min/q1/median/q3/max/
composite_best/n) for one `(kpi, section)` pair, or the well-level `Card` (value + best) when
`section == "well"`. A single-number `stat` (e.g. `"median"`) was considered but rejected: it would
need a second disambiguating param for connections anyway (which KPI) and the agent already gets
the whole distribution in one call either way, which is cheaper on tool-call budget (max 12 per
`03_ARCHITECTURE.md` §4) than asking for one statistic at a time.

Decision 2 — evidence for aggregations the pipeline never pre-computed: every number the static
export already carries (`kpis.json`, `ilt.json`, `reconciliation/*.json`, ...) already has a real
`evidence_id` resolvable via `/evidence/{id}` — those tools just pass the `Quantity` through
unchanged. But `rigstate_summary(well, t0, t1)` sums interval durations over an *arbitrary*
caller-chosen window that was never exported with its own evidence record. Per CLAUDE.md ("a
number without evidence is a bug"), the agent (`copilot/agent.py`) constructs one
`strata_pipeline.evidence.EvidenceRegistry` per `/ask` session and every tool that computes a new
number mints a real evidence record through it (`reg.quantity(...)`, same deterministic
`ev_<sha1(tool|params|sources)>` id scheme the pipeline itself uses) — not written to the on-disk
shards (this is a live, per-request computation, not an export artifact), but resolvable by the
`evidence(id)` tool and the verifier for the lifetime of that one request/session. The verifier
checks a claim's `evidence_id` against this session registry first, falling back to the on-disk
static shards, so both pass-through and freshly-minted claims verify the same way.

Decision 4 — which tools are "physics" for `full_minus_physics`: `07_DATA_AND_ALGORITHMS.md` §13
names this ablation ("physics tools disabled") without listing them.
`eval/strata_eval/run_ablation.py` treats a tool as "physics" when it derives from sensor/
classifier output or a DDR-vs-sensor comparison — `rigstate_summary`, `kpi_connection_times`,
`kpi_trips`, `ilt_breakdown`, `formation_stats`, `reconciliation`, `mismatches` — and leaves
`list_wells`, `well_summary`, `ddr_search`, `issues_query`, `evidence` available (metadata and
narrative lookups, nothing computed from channel data). This is the ablation meant to answer "how
much does the model lean on computed drilling metrics vs. just narrative/metadata", so the split
follows that question rather than, say, which pipeline module produced the underlying export file.

Consequences: a `rigstate_summary` evidence id is only ever valid within the session that minted
it (never shareable across sessions or persisted) — acceptable, since the recorder (T8.5) saves
the whole session trace including the evidence that validated each claim, and static-mode replay
never re-verifies, it just replays the recorded `CopilotEvent`s.

Decision 3 — verifier tolerance: `03_ARCHITECTURE.md` §4 says a claim must match evidence "to the
display precision shown", but `Claim` (the model's own structured output) has no `precision`
field and neither does `Evidence` — only the `Quantity` the tool returned had one, and that field
doesn't survive into a claim. Every `Quantity` in this codebase is written with `precision=2`
(every KPI/ILT/reconciliation export), so `copilot/verifier.py` compares `|claim.value -
evidence.value| <= 0.005` (half the last displayed digit at 2 decimals) rather than requiring an
exact float match, which would fail on ordinary display rounding (the model writing "6.15" for a
stored `6.1500000001`). If a future tool genuinely needs coarser precision, pass it through
`Claim.text` rather than changing this fixed tolerance.
