# STRATA Drilling Copilot — Engineering Audit and Remediation Plan

**Audit date:** 2026-10-13  
**Repository:** [sergeiredkin/strata-drilling-copilot](https://github.com/sergeiredkin/strata-drilling-copilot)  
**Baseline reviewed:** main at [717a5c51e6097129892c44d72c3b3920c13a7f62](https://github.com/sergeiredkin/strata-drilling-copilot/commit/717a5c51e6097129892c44d72c3b3920c13a7f62) (2026-10-13 05:25 UTC)  
**Type:** Read-only, source-based technical assessment and prioritized implementation backlog  
**Intended audience:** Project owner, architecture agent, implementation agent, independent reviewer, and domain expert.

> **Evidence standard.** "Confirmed" means directly observed in the cited code, tracked artifact, or GitHub Actions job metadata. "Reported" means the repository documentation states a test was completed, but the auditor did not independently rerun it. "Needs validation" describes a possible defect or unmeasured outcome. The audit did **not** download private/local Volve archives, execute the complete pipeline, run an independent browser test, or reproduce drilling metrics. Passing CI is not equivalent to field accuracy.

## Executive finding

STRATA is a credible, substantial **drilling analytics prototype with static demonstration and an emerging real-data pipeline**, not yet a validated production drilling copilot. The design's focus on evidence, abstention, deterministic computations, and advisory-only scope is appropriate. The immediate limitation is not the absence of additional AI agents or models. It is a lack of independent real-data truth, end-to-end release verification, complete measurement provenance, and evaluated live copilot behavior.

**Suggested release labels, not retrospective claims:**
- **Static UI demo:** code and fixtures exist; published deployment is **not confirmed operational** because the GitHub Pages build failed on the audited commit.
- **Real-data analysis:** one Volve well reported as locally validated in [backlog](../../tasks/BACKLOG.md); the other five are pending systematic independent verification.
- **Rig-state accuracy:** unmeasured on human-labelled real gold samples.
- **Live LLM copilot:** not implemented; the API currently emits a placeholder answer.
- **Industrial readiness:** not established; no operational-performance or safety claims.

**Stop rule:** Do not present an exported value as independently verified field truth unless its data lineage, source-unit validation, human reference or appropriate uncertainty, and reproduction path are available. Do not claim measured NPT savings or recommend rig controls.

## Evidence snapshot

| Evidence | Observed fact | Status |
|---|---|---|
| [CI workflow](../../.github/workflows/ci.yml), [run 38351315874](https://github.com/sergeiredkin/strata-drilling-copilot/actions/runs/38351315874) | Python job passed uv sync, Ruff, mypy, pytest; web and contracts jobs failed at pnpm/action-setup before executing tests; copy-lint passed | Confirmed |
| [GitHub Pages workflow](../../.github/workflows/pages.yml), [run 38351315869](https://github.com/sergeiredkin/strata-drilling-copilot/actions/runs/38351315869) | Pages build failed at pnpm/action-setup; deployment skipped | Confirmed |
| [package.json](../../package.json) | packageManager declares pnpm 12.10.1, Actions installs pnpm 9 | Confirmed configuration mismatch; root failure detail not independently recovered |
| [createDataSource.ts](../../apps/web/src/data/createDataSource.ts), [vite.config.ts](../../apps/web/vite.config.ts) | StaticSource receives absolute /data base while Pages serves under /strata-drilling-copilot/ | Confirmed code-path risk; test actual browser behavior |
| [wells.json](../../apps/web/public/data/wells.json) | All 9 committed demo wells have is_mock=true | Confirmed; legitimate for a clearly labelled fixture demo |
| [eval/rigstate_gold.csv](../../eval/rigstate_gold.csv), [eval.json](../../apps/web/public/data/eval.json) | Human gold CSV header only; copilot gold n_questions=0; ablation metrics and rig-state agreement null | Confirmed |
| [BACKLOG.md](../../tasks/BACKLOG.md) | One real-well smoke validation reported; five more pending. T8.4, T8.5, T9.2, T10.4 not done | Reported |
| [copilot.py](../../services/api/strata_api/routes/copilot.py) | /copilot/ask responds with live_mode_required stub, not an LLM agent | Confirmed |
| [real_well.py](../../pipeline/strata_pipeline/export/real_well.py) | Uses source object with sha256=n/a, returns empty hole sections, forces absent NPT flags to false | Confirmed |
| [rules.py](../../pipeline/strata_pipeline/rigstate/rules.py) | Rule R3 defaults undetermined trip direction to trip_out | Confirmed |
| [LICENSES.md](../../docs/LICENSES.md) | Equinor/Databricks-derived redistribution and commercial scope remains a documented open question | Confirmed unresolved issue; this is not legal advice |
| [README.md](../../README.md) | Status now accurately acknowledges implementation in progress; older “implementation not started” finding is resolved | Confirmed |

## Prioritized remediation backlog

Definitions: **P0** = must address before a defensible public real-data demonstration or trust claim; **P1** = essential to robust M4 and useful live copilot; **P2** = hardening, extension, or later-stage work. Items marked **investigate** are not asserted bugs. Each item needs one owner agent, an independent verifier, and preserved evidence of acceptance.

### P0-01 — Restore trustworthy CI and GitHub Pages deployment
**Status:** Confirmed failure.  
**Evidence:** [ci.yml](../../.github/workflows/ci.yml), [pages.yml](../../.github/workflows/pages.yml), [package.json](../../package.json), [CI run](https://github.com/sergeiredkin/strata-drilling-copilot/actions/runs/38351315874), [Pages run](https://github.com/sergeiredkin/strata-drilling-copilot/actions/runs/38351315869).  
**Do:** Retrieve precise pnpm/action-setup error logs; select an actually installable canonical pnpm version; align packageManager, lockfile, and all workflow install steps. Then ensure web lint, TS typecheck, Vitest, Vite build, generated-contract check, Python checks, copy-lint, Playwright E2E/a11y run on PRs. Verify whether E2E needs browser install/caching and set appropriate timeouts. Configure branch protection/required checks only after checks are stable.  
**Accept:** Two clean runs from a fresh checkout on the same commit; all configured checks pass; Pages deploy reports success; report includes workflow URLs and actual checks executed. A passing Python job alone is insufficient.  
**Owner:** CI/infra agent. **Verifier:** independent reviewer.

### P0-02 — Fix and test static-demo subpath / navigation behavior
**Status:** Confirmed absolute-path risk; browser outcome unverified.  
**Evidence:** [createDataSource.ts](../../apps/web/src/data/createDataSource.ts) constructs StaticSource('/data'), while [vite.config.ts](../../apps/web/vite.config.ts) changes the Pages asset base. [router.tsx](../../apps/web/src/app/router.tsx) uses BASE_URL as React Router basename.  
**Do:** Resolve static fetches using the Vite base URL in Pages builds while preserving root-path local mode; verify JSON, binary series chunks, evidence shards, recorded sessions, icons, route navigation, reload/back-forward, and a deep-link refresh. Confirm GitHub Pages SPA fallback behavior for direct nested URLs; deploy an intentional fallback or use routing that works on static hosting. Add a Pages-base Playwright smoke test.  
**Accept:** Open the published /strata-drilling-copilot/ URL from an uncached browser; /field loads real fixture JSON, a well workspace loads binary channel series, an evidence popover resolves, and direct navigation/reload works without 404. Preserve screenshots and browser console/network logs.  
**Owner:** frontend/infra agent. **Verifier:** browser E2E agent.

### P0-03 — Preserve an explicit, correct fixture-versus-real-data boundary
**Status:** Confirmed: published assets remain all mock; the real-data exporter is separate.  
**Evidence:** [wells.json](../../apps/web/public/data/wells.json), [generate_real.py](../../pipeline/strata_pipeline/export/generate_real.py), [README.md](../../README.md).  
**Do:** Maintain a visible FIXTURE/REAL label per well and export; avoid mixing fixture summaries, synthetic metrics, and real-derived computed values without row-level flags. Use separate build/export directories or manifests for fixtures and real data, with provenance assertions preventing accidental mixed publication. Ensure experimental real exports are not automatically shipped to GitHub Pages without licence and QA approval.  
**Accept:** CI test inspects every published well and evidence record for source-mode consistency; the UI never portrays generated fixture data as observed field measurements; two builds (fixture and real) have auditable, separate manifests.  
**Owner:** data/platform agent. **Verifier:** trust/UI reviewer.

### P0-04 — Build independent rig-state ground truth and validate recognition
**Status:** Confirmed missing reference labels.  
**Evidence:** [rigstate_gold.csv](../../eval/rigstate_gold.csv) header only; [RIGSTATE_GOLD_README.md](../../eval/RIGSTATE_GOLD_README.md); [rigstate_agreement.py](../../eval/strata_eval/rigstate_agreement.py).  
**Do:** Freeze sampling protocol before selecting cases. Manually label at least 200 ten-minute windows drawn across multiple wells, dates, drilling/tripping/connection/reaming/circulation and missing-data conditions; additionally oversample rare safety-relevant or confused states for diagnostics. Keep a representative prevalence sample separate from the challenge sample so reported overall accuracy is not biased. Record reviewer, ambiguous label policy, confidence, raw traces, timestamp, and source hash. A second domain reviewer should adjudicate disagreements when feasible. Do not let agents fabricate or see hidden gold labels while tuning.  
**Accept:** Locked gold-set manifest and labels, confusion matrix, macro-F1, per-state precision/recall, coverage and abstention rates, per-well metrics, CI regression report, and explicit residual error analysis. Pre-register numerical go/no-go thresholds with the domain owner before tuning; do not invent a passing percentage post hoc.  
**Owner:** domain expert (labels) + eval agent. **Verifier:** independent drilling reviewer.

### P0-05 — Make measurement and evidence lineage genuinely reproducible
**Status:** Confirmed incomplete file-level provenance in real export.  
**Evidence:** [real_well.py](../../pipeline/strata_pipeline/export/real_well.py) source entries include file=pipeline:real and sha256=n/a; [evidence.py](../../pipeline/strata_pipeline/evidence.py) creates deterministic IDs.  
**Do:** Connect exported KPI, ILT, reconciliation and QC quantities to actual archive/member/log identities, per-source SHA-256, channel names, time/depth windows, transformations, parameter/config hashes, code commit and export version. Audit evidence ID uniqueness and identity across runs when values or versions change; verify that each displayed Quantity resolves to a coherent source record and input dataset. Separate computational reproducibility from scientific correctness.  
**Accept:** Select 20 randomly sampled real-derived quantities, independently reconstruct inputs and recalculate each value to defined numerical tolerance; zero missing references and no stale/mismatched evidence hashes; reproducible manifest and script committed (without redistributing restricted raw data).  
**Owner:** data/provenance agent. **Verifier:** independent calculations reviewer.

### P0-06 — Represent unknown booked-NPT status as unknown, not zero
**Status:** Confirmed semantics risk; business impact needs validation.  
**Evidence:** [real_well.py](../../pipeline/strata_pipeline/export/real_well.py) converts absent npt_flag with bool(), then derives booked NPT from these values.  
**Do:** Preserve the three states reported true, reported false, and not provided/unknown. Adjust schema/API/UI to represent unavailable booked-NPT hours as N/A rather than zero when no reliable indicator exists; make absence of NPT metadata explicit. Distinguish measured nonproductive/inefficient time inferred from sensors from downtime booked by an operator.  
**Accept:** Missing NPT field never produces a claim of “0 hours reported NPT”; synthetic tests cover true/false/unknown; user-facing definitions explain what comparison is and is not supported.  
**Owner:** contracts/data agent. **Verifier:** drilling domain reviewer.

### P1-07 — Audit rig-state rule R3 and ambiguity handling
**Status:** Confirmed fallback behavior; real-world error frequency unmeasured.  
**Evidence:** [rules.py](../../pipeline/strata_pipeline/rigstate/rules.py), [classify.py](../../pipeline/strata_pipeline/rigstate/classify.py), [flags.py](../../pipeline/strata_pipeline/rigstate/flags.py).  
**Do:** Replace or explicitly justify “trip_out when direction unknown.” Compare unknown/ambiguous classification, enclosing-trip context, BITDEPTH trend, hookload/slips and block-motion sign conventions on gold windows. Record rule ID and margin for each decision. Verify that trip-in, trip-out, and connection durations propagate correctly to ILT.  
**Accept:** Unit tests for missing direction and ambiguous slips, a before/after confusion matrix on held-out samples, and no undeclared regression in trip KPIs.  
**Owner:** analytics agent. **Verifier:** independent domain/eval agent.

### P1-08 — Check QC order, source selection, and irregular sampling
**Status:** Investigate: known implementation risks with real, asynchronous WITSML channels.  
**Evidence:** [qc/pipeline.py](../../pipeline/strata_pipeline/qc/pipeline.py) calls unit auto-detection before sentinel filtering, although the unit detection helper documents clean input; [qc/reconcile.py](../../pipeline/strata_pipeline/qc/reconcile.py) picks the source log with most rows; [rigstate/preprocess.py](../../pipeline/strata_pipeline/rigstate/preprocess.py) bounded-forward-fills core channels.  
**Do:** Test sentinels/outliers influencing unit inference, channel conversions and QC survive rates; verify channel selection by overlapping operational coverage and quality, not only count. Sweep hold duration/resampling gap/hysteresis windows and compare how they change classification, interval boundaries and ILT. Preserve no-data gaps and avoid fabricated precision from forward-filled samples. Validate UTC/local time conversion around DST and mixed log sampling.  
**Accept:** Synthetic adversarial tests + real-well sensitivity report, channel-level provenance, explicit hold/staleness rules, and documented bounds beyond which the classifier abstains.  
**Owner:** data-quality agent. **Verifier:** independent time-series reviewer.

### P1-09 — Validate hole-section derivation and ILT baselines
**Status:** Confirmed missing real section export.  
**Evidence:** [real_well.py](../../pipeline/strata_pipeline/export/real_well.py) returns empty sections; all real KPIs currently group under an “unknown” section fallback.  
**Do:** Implement verifiable casing/hole-size section derivation from trusted source metadata or DDR with cited origin. Define low-sample and outlier-resistant composite-best behavior. Test ILT waterfall conservation, overlaps, zero/negative durations, gap exclusions and the sensitivity of “lost time” to P10/P90 baselines. Avoid calling baseline-relative excess time actual recoverable NPT.  
**Accept:** Manually validated section boundaries on at least two wells; test that total ILT equals category and section/day breakdowns within tolerance; sensitivity plots and uncertainty note attached to benchmark claims.  
**Owner:** analytics agent. **Verifier:** drilling domain reviewer.

### P1-10 — Systematic real-well integration, reproducibility and resource budget
**Status:** Reported: one Volve well live-validated locally; other five pending.  
**Evidence:** [BACKLOG.md](../../tasks/BACKLOG.md), [DATA_INVENTORY.md](../../docs/DATA_INVENTORY.md), [drilling_window.py](../../pipeline/strata_pipeline/ingest/drilling_window.py).  
**Do:** Run all six registered Volve wells from pinned source archives, recording elapsed runtime, peak RSS, coverage, dropped-data reasons, errors, channel mappings and stable output checksums. Investigate the DDR-driven 500-hour merge threshold across wells; ensure non-drilling workovers/campaign gaps are excluded appropriately. Compare fixtures and real results without assuming similar distributions.  
**Accept:** Per-well QA ledger for six wells, bounded memory/runtime in the intended workstation, repeat-run consistency and explicit pass/fail for each dataset; no “six wells validated” claim until done.  
**Owner:** data pipeline agent. **Verifier:** integration/performance reviewer.

### P1-11 — Distinguish heuristic confidence from empirical correctness
**Status:** Confirmed model semantics; empirical calibration not present.  
**Evidence:** [rigstate/intervals.py](../../pipeline/strata_pipeline/rigstate/intervals.py) defines p as share of decisions with relative margins above thresholds; [confidence.py](../../pipeline/strata_pipeline/confidence.py) maps coverage/sample/heuristic margin scores into levels.  
**Do:** Call this a heuristic decision-strength/coverage metric unless calibrated with truth labels; test whether higher scores genuinely predict higher classification accuracy. Evaluate reliability plots/calibration or rename the field to avoid the implication of calibrated probability. Keep data completeness separate from model correctness.  
**Accept:** Plain-language UI semantics, stratified accuracy-vs-score assessment and never display “90% probability correct” without calibration evidence.  
**Owner:** evaluation agent. **Verifier:** domain/product reviewer.

### P1-12 — Build a bounded, evidence-grounded live Copilot (T8.4/T8.5)
**Status:** Confirmed not yet built.  
**Evidence:** [copilot.py](../../services/api/strata_api/routes/copilot.py), [product spec](../../docs/01_PRODUCT_SPEC.md), [BACKLOG.md](../../tasks/BACKLOG.md).  
**Do:** Start with read-only typed tools: read rig state/windows, KPI/ILT breakdown, DDR quotes and provenance; strict validation and resource limits. Verifier must parse numerical claims and link each to a specific tool result/evidence ID with unit and context. Reject mismatched, stale, unsupported or invented values; support correct refusal/insufficient_data. Persist recorded sessions, model/prompt version, tool traces, time/cost/usage and context. Do not permit command execution, plant control or unrestricted file/network tools.  
**Accept:** Every response has verifiable structured claims; seeded tests for unsupported number, contradictory DDR, low coverage, missing source, stale evidence and unit mismatch; no silently asserted unsupported value. Human technical review before public live demo.  
**Owner:** copilot agent engineer. **Verifier:** adversarial independent eval agent.

### P1-13 — Create a frozen expert Copilot evaluation and ablation suite
**Status:** Confirmed absent.  
**Evidence:** [eval.json](../../apps/web/public/data/eval.json) has n_questions=0 and null ablations; [eval/gold](../../eval/gold/) is empty.  
**Do:** Author at least 25 expert questions covering connections, trips, ILT, DDR mismatch, sensor quality, ambiguous operations, numerical math, units, and known insufficient-data cases. Lock reference answers and evidence, keep a held-out set, compare no_tools, simple_rag, full and suitable reduced-tool variants once each actually exists. Evaluate correctness, verified-claim fraction, unsupported-number count, abstention precision/recall, latency and dollar cost. Run repeated seeds where nondeterminism matters.  
**Accept:** Versioned gold set and executable report; no null metric is presented as a pass; errors categorized and independently reviewed. Do not release blanket “AI is accurate” claims based on an untested demo.  
**Owner:** evaluation lead + domain expert. **Verifier:** reviewer with no role in prompt development.

### P1-14 — Resolve licence and publication boundaries; add code licensing
**Status:** Confirmed open question, not a finding of infringement.  
**Evidence:** [LICENSES.md](../../docs/LICENSES.md), [raw-data manifest](../../data/raw/MANIFEST.json); no root LICENSE file at baseline.  
**Do:** Obtain/read the complete current Equinor Open Data Licence and Databricks distribution terms; explicitly assess source-data redistribution, derived-series exports, screenshots, attribution, commercial demos and any legacy NC/SA restriction with qualified advice where required. Keep raw archives untracked, audit Git history for inadvertently included restricted data, and select a clear open-source license for original code. Track separate dataset/asset licenses in the readme and deployed product.  
**Accept:** Written decision and attribution checklist signed off before shipping any derived real-data files; root source-code license present; publication manifest references permitted content only.  
**Owner:** project owner/licence reviewer. **Verifier:** legal/data-governance reviewer if commercial use planned.

### P1-15 — Public-repository, API and deployment security review
**Status:** Investigation; no exploit independently demonstrated.  
**Evidence:** [services/api](../../services/api/), [data_access.py](../../services/api/strata_api/data_access.py), [workflows](../../.github/workflows/).  
**Do:** Validate route/path constraints, path resolution under data_dir, read-only authorization boundary, untrusted strings shown in UI, markdown/HTML rendering and LLM prompt injection from DDR narratives. Scan dependencies, secrets, committed artifacts and build permissions. Minimize GitHub Actions permissions except Pages where needed; enable dependency alerts and review workflow action pinning. API has no auth by design for the open demo, so do not publish it as a private-field-data service without security architecture.  
**Accept:** Documented threat model, no high-severity unmitigated issues in agreed scanner scope, injection tests for copilot, permission review, and deployment boundaries explicit.  
**Owner:** security agent. **Verifier:** human reviewer.

### P2-16 — Production-style verification, UI review and performance
**Status:** Tests/specifications exist; full external verification pending.  
**Evidence:** [testing and acceptance](../../docs/08_TESTING_AND_ACCEPTANCE.md), [web e2e](../../apps/web/e2e/demo.spec.ts), [backlog](../../tasks/BACKLOG.md).  
**Do:** Run Playwright on fresh clone in CI and on actual Pages deployment; check both themes, unit toggle, large time windows, axis sync, mouse/keyboard navigation, accessible labels, chart frame rate, 450 kB initial gzip bundle budget and less-than-25 MB per-well export target. Have the owner visually review against the comps; provide screenshots of any failed check.  
**Accept:** Signed-off visual/E2E report, measured FPS/bundle/export sizes, reproducible browser/browser-version conditions, and no unacknowledged P0 errors.  
**Owner:** frontend/performance agent. **Verifier:** project owner.

## Execution sequence / dependencies

**Phase A — public-demo hygiene (first):** P0-01, P0-02, P0-03, licence screening in P1-14. Deliver a working, honestly labelled fixture-only GitHub Pages build. No drilling-accuracy claim.

**Phase B — establish real-data truth:** P1-08 and P1-10 in parallel with expert labels P0-04; resolve P1-07, P0-06, P0-05 and P1-09 before substantive performance claims. Record a baseline commit, source dataset hash and measurement protocol.

**Phase C — qualify scientific outputs:** P1-11 and P1-13; establish the locked test set. Only then optimize rig-state/ILT logic based on out-of-sample evidence.

**Phase D — agent release:** P1-12 with explicit security checks P1-15; run real-data end-to-end and P2-16 acceptance before advertising a working live copilot.

**Avoid scope drift:** Defer Utah FORGE blockage work, P1 formation/precursor models, replay and P2 physics until the core drilling loop has defensible results. Retain existing [implementation plan](../../docs/02_IMPLEMENTATION_PLAN.md) as the task-level build roadmap; this audit is the **quality gate**, not a competing product backlog.

## Human-only input and sign-off

- [ ] **Owner / domain expert:** Provide 200 real rig-state labels following a predeclared sampling plan. Do not ask a coding agent to invent truth.
- [ ] **Owner / domain expert:** Provide at least 25 Copilot questions, expected answers, evidence windows and legitimately unanswerable cases.
- [ ] **Owner:** Review whether inferred slips/connection/tripping rules match drilling practice on Volve curves; document assumptions.
- [ ] **Owner:** Review and approve visual screens against actual design comps and the static public demo.
- [ ] **Owner/licence reviewer:** Resolve real-data derived-publication terms before upload.
- [ ] **Owner:** Approve any changes that affect operational interpretations, contracts, dataset release or externally published results.

## Harness / graph / loop engineering pilot (after Phase A)

Use existing FirstMate + Python/SQLite job queue; do not migrate to LangGraph solely to add a framework. Design a bounded **issue-to-accepted-PR loop**:

1. Freeze task objective, source commit, expected files, budget and acceptance tests in a machine-readable task contract.
2. Architect agent plans; implementer writes in an isolated worktree with scoped filesystem/network permissions; tests run deterministically.
3. Failure analyzer classifies syntax, test, data, inference, or environment errors and returns targeted evidence for repair; cap retries (suggest 2–3), wall time and monetary spend.
4. An independent model reviews passing changes; deterministic tests and hidden gold set remain final authority. Prevent agents editing evaluator logic, gold answers or original acceptance thresholds without human approval.
5. Integration and domain gates run; on uncertainty, repeated error, data provenance change or operational safety issue, stop and escalate with complete evidence.
6. Persist execution trace, commits, tool versions, token cost, elapsed time, retries, human intervention count and final review decision in SQLite/JSON.
7. Compare at least 10–20 reasonably similar tasks with and without loops: **accepted tasks per owner-hour**, cycle time, cost per accepted PR, first-pass acceptance, reopen/defect rate. Do not equate number of agents or commits with productivity.

**Suggested first pilot tasks:** fix pnpm CI mismatch; resolve Pages /data base path; add NPT unknown-state contract tests. **Keep expert labelling out of autonomous loops.**

## Commands and review artefacts

On a machine with the repository cloned and dependencies installed:

- <code>make setup</code> — install JS and Python dependencies.
- <code>make contracts-check</code> — ensure generated TS/Zod/Python contracts are current.
- <code>make lint && make typecheck && make test</code> — standard static checks and tests.
- <code>make e2e</code> — Playwright browser checks (install browser prerequisites first).
- <code>make fixtures</code> — regenerate explicitly marked synthetic assets.
- <code>make pipeline WELL=15_9-F-11_A</code> — run a real well only when permitted raw data are installed locally.
- <code>make reproduce WELL=15_9-F-11_A</code> — exercise the reproduction entrypoint; confirm its documented inputs/outputs, it is not a substitute for expert validation.

**For every closed item attach:** issue ID, baseline and fix SHA, changed-files list, exact command/test environment, green CI URL, failing-before/passing-after test, relevant screenshots or evidence hashes, limitations, and independent verifier decision.

## Release gates (binary decision)

| Gate | Requirement | State at audited commit |
|---|---|---|
| G0 — static demo | Pages green; asset paths, navigation, and end-to-end fixture demo work; mock labels unmistakable | **NOT MET** |
| G1 — real data | At least two independently reviewed wells, documented source hashes, QC and sensor/DDR alignment, no invented metrics | **NOT MET** |
| G2 — rig-state trust | Locked human gold set and per-class results, known ambiguity and error bars, held-out checks | **NOT MET** |
| G3 — measurement provenance | Real quantities reproducible from source, units and method; missing NPT handled truthfully | **NOT MET** |
| G4 — live AI copilot | Actual tools/verifier/abstention, expert gold and ablation metrics, safe read-only operation | **NOT MET** |
| G5 — external/industrial positioning | Licence cleared, security review, observed performance, owner sign-off; no control or NPT-saving guarantees | **NOT MET** |

**The next milestone is G0, then G1–G3; do not skip directly to G4 because the UI already contains a Copilot panel.**

## Audit limits, re-audit policy and how to use this document

This assessment represents a snapshot, not a continuously updating monitoring service. Existing CI results were read from GitHub Actions, but application code was not executed by the auditor. Reported F-11 A validation is a repository claim, not an independently observed field-accuracy result. Confirm version changes before using findings as current.

When an agent closes an item, update its status through a separate follow-up review (ideally a PR linked to this report), cite passing evidence, and explicitly supersede findings made obsolete by later commits. A newly implemented feature is not automatically equivalent to a validated feature. Treat this as a living review checklist, with changes documented rather than silently marking all tasks completed.
