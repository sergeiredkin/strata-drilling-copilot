# Sample: Volve well 15/9-F-11 A (real data excerpt)

A small, real excerpt from the Equinor Volve dataset (see `docs/LICENSES.md` — CC BY-NC-SA 4.0 /
"Equinor Open Data Licence", no-resale, attribution-if-shared; this repository is not resold, and
this attribution notice satisfies the "if shared" clause). Used by `pipeline/tests/test_ingest_*`
as a real-structure regression fixture — not synthetic, so a parser bug that only shows up on
real WITSML/DDR quirks (irregular cadence, multi-registration wellbores, local-vs-UTC timestamps
— see `docs/DATA_INVENTORY.md`) actually gets caught.

**Contents** (164 KB total):
- `witsml_root/.../log/1/26/2/00001.xml` — first 50 `<data>` rows of one real time-indexed log
  chunk (originally ~4 MB / 10,000 rows; truncated here, structure and header untouched) plus the
  real `_wellboreInfo/*.xml` that identifies it as wellbore "NO 15/9-F-11 A".
- `ddr/15_9_F_11_A_2013_05_{15,25}.xml` — two full, real Daily Drilling Report days.
- `survey/Volve F_F-11_159-F-11 A_159-F-11 A_ACTUAL` — the full, real directional survey export
  (already small, 319 stations).

**Attribution**: Data publisher: Equinor ASA. Data owners: Equinor (operator), ExxonMobil
(partner), Bayerngas (partner), and the Norwegian Petroleum Directorate (NPD). Source: Volve
field dataset, released via equinor.com / Databricks Marketplace.
