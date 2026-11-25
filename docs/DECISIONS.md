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

## Decision template

Record date, title, status, problem, considered options, selected approach, rationale, implications, verification and related commit or issue.
