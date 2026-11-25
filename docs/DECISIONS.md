# Architecture and research decisions

## 001 — Population and geography (2026-11-22)

**Accepted:** Study Medicaid beneficiaries ages 0–17 and 18+ across NY, NJ, MD, VA and PA. Use age-appropriate measures and independent subgroup evaluation. Five-state coverage is a project target; each source's actual coverage will be verified separately.

## 002 — Data acquisition strategy (2026-11-22)

**Accepted:** Start with publicly accessible actual Medicaid spending, quality and discharge data. Train aggregate forecasts and discharge-level models only when the required fields and adequate samples are available. Pursue institutional authorization for longitudinal claims. Synthetic records may support testing; synthetic performance will be identified explicitly.

## 003 — Initial source and analytical database (2026-11-22)

**Accepted:** Start with CMS quality and enrollment data because both provide explicit state fields and accessible, manageable public records. Preserve raw JSON, create validated CSV outputs and a local SQLite database for the initial research pipeline. Retain original source flags and versions; use final enrollment reports for longitudinal state trends. This provides a reproducible local foundation that can later migrate to PostgreSQL. Provider spending data requires separate geographic and population assessment.

## 004 — Spending release handling (2026-11-23)

**Accepted:** Preserve official CMS financial archives and HHS national Parquet releases. Extract exact five-state CMS workbook lines with source provenance and validate totals separately from overlapping detail. Use Parquet for large HHS data and verify published checksums. Do not label provider-attributed national records as five-state or age-specific until justified by the available data. Avoid unfiltered drug placeholder sums and avoid double-counting across payment sources.

## 005 — Provider geography and community context (2026-11-23)

**Accepted:** Preserve provider enrollment segments with their state, dates and plan/status fields. Use overlap and explicit ambiguity checks for provider-level geographic exploration. Do not assume one NPI identifies a single state. Join HRSA and Census on exact five-character county-equivalent FIPS. Use the official ACS bulk files when an API key is unavailable. NY discharge analysis is a single-state sub-study until comparable records are secured for other states.

## 006 — Enrollment Silver grain and missing values (2026-11-24)

**Accepted:** Use final CMS reporting versions, one row per state-month; preserve all source records in Bronze. Keep enrollment fields as nullable integers and month as a date in Parquet. Track missing months and unavailable counts rather than impute them. Do not derive Medicaid-only adult/child totals from incompatible Medicaid/CHIP measures. Use separate cleaning scripts for each source before Gold integration.

## 007 — Core Sets Silver semantics (2026-11-24)

**Accepted:** Preserve original rate strings, notes and all measure variants; create nullable numeric rates and explicit reporting status, unit and performance direction. Use the seven-field composite key. Reject unknown unit definitions or flags pending review. Validate quartiles by direction, not universal numeric ordering. No imputation, suppression reconstruction or unweighted aggregation of incompatible cohorts. This supports reproducible population-level comparisons without pretending to have individual care histories.

## 008 — CMS-64 Silver financial grain (2026-11-24)

**Accepted:** Preserve signed whole-dollar integer amounts, all source labels and row provenance. Key by state/year/program/source row rather than category. Isolate the exact main reported net total and independently validate both main worksheet rollups against all three funding columns. Tag verified additive detail; retain later sections without assuming their relation to main net totals. Do not aggregate subtotals with components or infer age-specific spending. Additional section-level semantic mapping is deferred.

## 009 — HHS spending and enrollment linkage (2026-11-24)

**Accepted:** Use DuckDB Parquet scans and compact 84-month masks per NPI/state rather than expanding segments directly. Check identifier format/checksum, code format, count thresholds, months and finite payment; preserve all raw values and audit exclusions. Require one billing-provider state in national enrollment evidence for the month and an active Medicaid plan status before including a cell in exploratory in-scope rollups; assume null end through study end but flag uncertainty. Do not use the other NPI as a fallback. Exclude nonconforming code strings and ≥$1B absolute cell values from exploratory rollups, not raw audits. This is not actual claim state, age-specific spending, product validation or proof of waste. The matched subset is highly selected and requires sensitivity analysis before models. Retain separate HCPCS/NDC tables and never sum unique patient counts across cells.

## Decision template

Record date, title, status, problem, considered options, selected approach, rationale, implications, verification and related commit or issue.
