# Industry review and positioning

Reviewed from public abstracts only (full texts paywalled on OnePetro — obtain PDFs before quoting publicly).

## SPE-227235-MS — "Novel Real-Time Data Analytics Approach for Optimizing Drilling Operations: A Case Study"
Albahri, Gamal, Shaikh — MEOS GEO, Manama, Sept 2025. Rig sensor data integrated with daily drilling reports;
KPIs for drilling, tripping, connections; benchmarking across rigs/operation/equipment in dashboards. States
invisible lost time ≈ 25 % of operations and "up to 10 %" time/cost saving in a field case. ML (ROP prediction,
hazard prediction, formation auto-classification) described as being added.

## SPE-229231-MS — "From Reactive to Proactive: Machine Learning-Powered Drilling Analytics for Operational Excellence"
Gamal, Omer — ADIPEC, Abu Dhabi, Nov 2025. Integrates geomechanics, offset wells, stuck-pipe incidents and NPT
logs; Gradient Boosting / Random Forest vs linear regression to predict instability risk; recommendation engine
for WOB/RPM/mud weight. Abstract reports no quantitative metrics.

## Assessment
Both describe **established industry practice** (rig-state KPIs and ILT since the 2000s–2010s, DDR integration,
tree-ensemble hazard/ROP models, advisory parameter engines), valuable for scale of deployment rather than
method novelty. Gaps visible in the abstracts: undefined ILT baseline, no validation scheme or metrics, no
uncertainty, best-case ("up to") results.

## STRATA positioning (what we show that they don't publish)
| Capability | Typical published practice | STRATA |
|---|---|---|
| Invisible lost time | Headline % without defined baseline | Defined composite best, per-category result, one-command reproduction (PR-1) |
| DDR integration | Merged into dashboards | Measured booked-vs-measured matrix with tolerance (PR-2) |
| Formation / hazard ML | Tree ensembles, metrics not reported | Leave-one-well-out, calibrated, baseline-compared, abstains; events as precursors not scores (PR-3, PR-4) |
| Parameter recommendations | WOB/RPM/MW engine | Out of scope by design — advisory analytics only |
| AI answers | Not covered | Tool-grounded copilot, per-number verifier, ablations (PR-5) |
| Physics | Not mentioned | T&D, MSE, surge/swab screening (PR-6) |
Pitch: complementary to fleet-scale vendor systems — open, reproducible, and honest about its own error bars.
Do not name vendor products in the UI.
