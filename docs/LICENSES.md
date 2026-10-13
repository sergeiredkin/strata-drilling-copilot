# Licences — public data sources (T2.1)

STRATA is built only on public data. This file records, verbatim where possible, the licence
terms under which each dataset was obtained, and what that means for this repository.

## 1. Equinor Volve (`data/raw/equinor_volve/`)

### What we actually have access to
Downloaded 2026-10-12 via the **Equinor listing in Databricks Marketplace**
(`marketplace.databricks.com`, provider "Equinor ASA") — Equinor retired the old direct-download
"Volve Data Village" ZIP page; this is now the only access path. It requires a free Databricks
account and a manual "Get instant access" click-through; there is no longer a stable public URL
to the files themselves. See §3 for exactly how this was done.

Three of the archives offered there were downloaded (sha256 in `data/raw/MANIFEST.json`):
`Volve_WITSML Realtime drilling data.zip`, `Volve_Reports.zip`, `Volve_Well_technical_data.zip`.
Seismic, reservoir-model, production, and full-field well-log archives were **not** downloaded —
out of scope for a drilling-analytics pipeline, and multiple terabytes for the seismic ones (full
list in `data/raw/MANIFEST.json`'s `skipped` field).

### Licence text, as found
Equinor bundles a `license.txt` inside every Volve archive (identical text in all three we
downloaded, confirmed by diff). Quoted verbatim:

> Thank you for your interest in the Volve dataset. Equinor hope you find the dataset useful and
> that you can apply it in an innovative and useful way.
>
> Data publisher: Equinor ASA
> Data owners: Equinor (operator), ExxonMobil (partner), Bayerngas (partner) and Norwegian
> Petroleum Directorate (NPD)
> Published via: https://www.equinor.com/
> The data is published under Creative Commons Attribution 4.0 International license (CC BY NC
> SA). (https://creativecommons.org/licenses/by-nc-sa/4.0/)
> The data shall not be resold.
> If shared, the data owners shall be attributed.
>
> Disclaimer
> The users of the information and data are expressly informed that the data provided by Equinor
> and the former Volve Licence partners is provided on an "as is" basis and may contain errors
> and omissions. Equinor and former Volve licence partners provide no warranties, expressed or
> implied, either relating to the content or to the relevance of the data. Equinor disclaims any
> liability for errors and defects associated with the data to the maximum extent permitted by
> law. Equinor and the former Volve Licence partners shall not be liable for any direct or
> indirect losses as a result of use of the data or concerning possible infringement of any
> intellectual property and/or patent rights of a third party.

Note this bundled file is dated 2018-08/09 and names **CC BY-NC-SA 4.0** — the *original* 2018
Volve licence. Equinor's current Volve page (equinor.com/energy/volve-data-sharing) states that a
newer **"Equinor Open Data Licence"** superseded CC BY-NC-SA in September 2020 and applies
retroactively to all Volve data; that page grants "academic institutions, students and
researchers permission to use this dataset... without further written permission." The Databricks
Marketplace listing itself (the current, authoritative distribution channel) repeats the same
core terms in its own disclaimer, without the "NC" (non-commercial) qualifier:

> The data set shall not be resold. [...] provided on an "as is" basis and may contain errors and
> omissions. [...] no warranties, expressed or implied [...] Equinor disclaims any liability for
> errors and defects [...] shall not be liable for any direct or indirect losses as a result of
> use of the data, or concerning possible infringement of any intellectual property and/or patent
> rights of a third party.

We did not obtain the full, standalone text of the "Equinor Open Data Licence" document itself
(it sits behind the Databricks login) — only the listing's disclaimer and the bundled 2018
`license.txt`. Both agree on the operative restriction: **no resale, attribution if shared, as-is
with no warranty.** Neither says anything about redistribution, publishing derived analysis, or
non-commercial-only use beyond that.

### What this means for STRATA
- **Not resold** — STRATA is free and open source; nothing is sold.
- **Attributed if shared** — this file, `docs/01_PRODUCT_SPEC.md`, and the app's own copy credit
  Equinor/the Volve licence partners wherever Volve-derived numbers are shown.
- **As-is, no warranty** — matches STRATA's own stance (`<Num>` + evidence + confidence badges;
  nothing here claims certified accuracy).
- Raw Volve files themselves are **not** committed to this repository (`data/raw/` is
  gitignored) — only derived, aggregated exports (rig-state classifications, KPIs, evidence
  records) ship in `apps/web/public/data/`, which is consistent with "shall not be resold" and
  the academic/research permission grant.
- **Open question, not yet resolved**: whether the *processed exports* we publish count as
  "sharing" the data (triggering the attribution clause — already satisfied) versus something the
  older NC term would restrict if it still legally applies. Given the Databricks listing (the
  *current* authoritative source) no longer states an NC restriction, and Equinor explicitly
  grants academic/research use, we're treating this as compliant for an educational open-source
  project — not resold, attributed, no warranty claimed. Flagging here rather than asserting
  certainty, since we never saw the full "Equinor Open Data Licence" document text itself.
- Personal note (not a repo concern): Equinor logs name/email/company/date of download for
  whoever accesses the dataset via Databricks — that's between Equinor and the Databricks account
  holder, not data that flows into this repository.

### Credit
Data publisher: Equinor ASA. Data owners: Equinor (operator), ExxonMobil (partner), Bayerngas
(partner), and the Norwegian Petroleum Directorate (NPD).

### Formation tops (`data/raw/volve_well_picks/Volve_well_picks_modified.csv`)
Not obtained via Databricks Marketplace — none of the three archives downloaded there have
per-well formation tops (`docs/DATA_INVENTORY.md` §1), and NPD/Sodir's own public tops layer has
no records for these development wells either. Sergei approved (2026-10-13) using a third-party
GitHub redistribution instead of waiting on the un-downloaded, multi-GB `Well_logs*.zip` archives:
`github.com/yohanesnuwara/volve-machine-learning`'s `Volve_well_picks_modified.csv`. The *repo* is
MIT-licensed, but that licence covers the repo author's own code, not Equinor's data riding along
in it — the CSV's content (formation names carrying Equinor's own "VOLVE" naming convention, full
34-wellbore Volve coverage) is treated as the same Volve dataset under the same terms as §1 above,
same attribution requirement, same "not resold." sha256 recorded in `data/raw/MANIFEST.json`
alongside the Databricks-sourced files. Not yet verified byte-for-byte against an Equinor-original
copy of the same file (see `docs/DATA_INVENTORY.md` §1 for what would close that out).

## 2. Utah FORGE (Geothermal Data Repository / OpenEI)

**Licence: CC BY 4.0** (Creative Commons Attribution), confirmed via `data.openei.org`'s own
footer ("Content is available under Creative Commons Attribution 4.0 unless otherwise noted") and
multiple individual dataset listings (e.g. Well 16A(78)-32 Drilling Data, DOI 10.15121/1776602).
Unambiguous and genuinely open — permits redistribution, commercial use, and derivative works,
with attribution.

**Status: blocked on infrastructure, not licence, as of 2026-10-12.** The hosting platform is
mid-migration:
- `openei.org` (the wiki with the real per-well pages and file links,
  `openei.org/wiki/Well_16A(78)-32` etc.) returns `503 Under Maintenance` site-wide.
- `gdr.openei.org` and `data.openei.org` respond (`200`), but submission detail pages return "No
  data found," and `gdr.openei.org/sitemap.xml` is empty — the current index has nothing in it.
- `catalog.data.gov` entries for the same datasets 404.
- A handful of raw file blobs under old numeric IDs (e.g.
  `gdr.openei.org/files/1292/16A(78)-32 Schlumberger.zip`) still resolve directly, but without a
  working index there's no reliable way to enumerate the *right* files (daily reports, 1-second
  Pason drilling CSVs, surveys) for our three wells (16A(78)-32, 16B(78)-32, 58-32) without
  guessing stale numeric IDs.

No FORGE files have been downloaded. Retry once the site is back; see
`data/raw/MANIFEST.json`'s `forge` field for the same status in machine-readable form.

## 3. How the Volve data was actually obtained (for reproducibility)

1. Sign up for a free Databricks account.
2. Databricks → Marketplace → filter provider "Equinor" → open the Volve listing → "Get instant
   access" → "On Databricks" (needs Unity Catalog) or "On external platforms" (Delta Sharing) if
   Unity Catalog isn't available on your workspace tier.
3. Wait up to an hour for the product to land in Catalog Explorer, under a `Volumes` node (not SQL
   tables — Equinor ships the original Volve Data Village file tree as-is).
4. Download the three archives listed in `data/raw/MANIFEST.json` directly from the Volumes file
   browser (small enough for the in-browser download button at 162 MB–2.4 GB).
5. This is a manual, authenticated, click-through process — there is no scriptable/anonymous URL,
   which is why it isn't automated here.
