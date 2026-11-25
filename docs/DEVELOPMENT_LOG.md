# Development log

This chronological record documents completed work, evidence, decisions and next steps. Add a dated entry per development session or milestone using the format below.

## 2026-11-22 — Project scope and documentation foundation

- **Completed:** Connected to the existing GitHub repository, cloned its `main` branch, inspected the existing pediatric prototype, and established the revised child-and-adult, five-state scope. Defined five analytical modules and the data acquisition-first roadmap.
- **Evidence:** Initial pediatric prototype and its tracked evaluation remain available in repository history; the evaluation records insufficient training observations. No new predictive model has been trained.
- **Decision:** Use accessible public real-world Medicaid data for the first beta, then pursue authorized longitudinal claims for individual predictions.
- **Verification:** Documentation review and Git diff checks. No application behavior changed.
- **Next:** Acquire and profile initial public datasets; establish reproducible ingestion and a state-aware data schema.

## 2026-11-22 — Research and beta documentation alignment

- **Completed:** Updated the research proposal (Version 2.0) and beta user guide (Version 3.0) to align with the five-state child-and-adult scope, age-appropriate measures, five analytical modules and documented development workflow.
- **Verification:** Reviewed both rendered PDFs and confirmed the revised versions were saved. Updated the project scope reference. No new data acquired or models trained in this documentation milestone.
- **Next:** Acquire and profile public datasets, documenting actual geographic and age coverage.

## 2026-11-22 — Milestone 1, initial public data acquisition

- **Completed:** Retrieved official CMS 2024 Child and Adult Core Set and enrollment responses for NY, NJ, MD, VA and PA. Implemented reproducible acquisition, offline rebuild, CSV output, SQLite tables and curated views.
- **Results:** 1,142 quality records (741 child, 401 adult); 1,100 enrollment reporting records, of which 550 are final. The acquisition report records source URLs, schema, hashes, row counts and missing values.
- **Verification:** SQLite integrity check passed, source counts and state coverage verified, final reporting keys unique, all 3 existing pediatric unit tests passed.
- **Limitations:** Aggregate quality data covers one reporting year; nonnumeric rates and historical missing adult enrollment fields remain explicitly identified. Spending data, hospital discharge data and restricted claims have yet to be acquired for this phase.
- **Next:** Acquire CMS expenditure and HHS provider spending data; review geographic attribution before developing analytical measures.

## 2026-11-23 — Milestone 1, expenditure and provider spending acquisition

- **Completed:** Downloaded official CMS-64 FY 2018–2025 ZIP archives and both national HHS T-MSIS provider spending Parquet releases; produced five-state CMS financial detail and totals CSVs and a downloadable ZIP package.
- **Results:** Eight archives, 12,595 five-state detail rows, 80 exact reported totals. HHS HCPCS 3,072,545,478 bytes and NDC 234,635,252 bytes.
- **Verification:** All source ZIP integrity checks passed; HHS files match published SHA-256 and length; all 80 total lines reconcile with funding shares. Bundle passed ZIP integrity check; existing three unit tests passed.
- **Limitations:** HHS extracts are national and lack beneficiary state/age attribution. CMS financial detail includes overlapping categories and adjustments. Full spending data has not yet been profiled or loaded into the analytical database.
- **Next:** Profile HHS data efficiently, assess provider geography, integrate verified CMS financial tables and acquire hospital data.

## 2026-11-23 — Milestone 1, provider and context dataset acquisition

- **Completed:** Acquired HHS provider enrollment segments, NY 2024 Medicaid-primary SPARCS discharge records, county HRSA 2024–2025 and Census 2020–2024 ACS tables. Implemented reproducible acquisition and packaged two download archives.
- **Observed:** 3,648,557 five-state provider segments, 307 matched county-equivalents and 635,606 NY discharges (159,975 pediatric and 475,631 adult). Provider segments are not unique providers. The national file matches its published SHA-256.
- **Verification:** Five-state provider output counts independently confirmed; HRSA and ACS keys match; all NY payer/year rows and official API count reconciled; ZIP integrity checks and existing unit tests passed.
- **Limitations:** Comparable NJ, MD, VA and PA discharge files require access arrangements. The public provider source cannot establish beneficiary state or age. No model training occurred.
- **Next:** Profile spending schemas, document provider linkage ambiguity, integrate financial/county data, assess accessible aggregate hospital comparisons.

## 2026-11-24 — Silver cleaning lab 01: CMS enrollment

- **Completed:** Profiled the existing 1,100-row source, verified its acquisition checksum, selected final reporting versions, converted dates and five enrollment counts, preserved footnotes and missing values, and generated CSV/Parquet Silver outputs.
- **Results:** 550 final state-month rows, 477 changed matched preliminary counts, 5 preliminary-only July 2026 rows excluded, 44 missing historical months per state, 430 missing final adult counts. All 545 reconcilable Medicaid/CHIP totals passed. See the [lab](ENROLLMENT_CLEANING.md) and [report](../reports/enrollment_cleaning.json).
- **Verification:** Schema, state, date, version, numeric, uniqueness and reconciliation checks passed, and Parquet row-count round trip passed. All seven unit tests passed, including four new targeted enrollment cleaning tests.
- **Next:** Clean CMS Core Set quality measures with suppression-aware semantics. No model trained.

## 2026-11-24 — Lab 02: CMS Core Sets Silver

- **Completed:** Profiled the actual 2024 five-state CMS quality extract and implemented `clean_core_sets.py`, CSV/Parquet outputs, `reports/core_sets_cleaning.json`, five targeted tests and `docs/CORE_SETS_CLEANING.md`.
- **Results:** 1,142 rows preserved (741 Child, 401 Adult); 1,048 reported numeric rates and 94 unavailable rates retained as null with source status. Zero duplicate composite keys; 25 output columns. All five states preserved.
- **Verification:** State identity, program, key, flags, units, numeric types, percentage bounds and directional quartile constraints passed. Full Parquet equality verified; 12 unit tests passed.
- **Limitations:** Aggregate published quality measures have distinct cohorts, methods, age ranges and units. No patient-level care-gap detection, individual risk prediction or model training performed.
- **Next:** CMS-64 expenditure cleaning and reconciliation.

## 2026-11-24 — Lab 03: CMS-64 expenditure Silver

- **Completed:** Verified both input hashes against acquisition, profiled and cleaned 12,595 worksheet rows and 80 exact main net totals, implemented `clean_cms64.py`, CSV/Parquet outputs, `reports/cms64_cleaning.json`, six tests and `docs/CMS64_CLEANING.md`.
- **Results:** All rows preserved, including 432 negative total amounts and 8,220 zeros. Repeated category labels create 115 extra category-key rows but no duplicate worksheet keys. Flagged 6,370 additive main components/adjustments, 160 main subtotal/total lines and 6,065 later lines outside the main net sum.
- **Verification:** All 12,595 funding splits, 80 worksheet balance and net identities and 80 report extracts reconcile; both Parquet full-equality checks passed. All 18 tests passed.
- **Limitations:** Annual financial reporting rather than beneficiary-level payments; no age breakdown, no proof of waste, no comprehensive mapping of later worksheet sections, no model trained.
- **Next:** HHS spending and provider enrollment cleaning.

## Entry template

- Date and milestone:
- Objective:
- Work completed and files changed:
- Data sources or decisions:
- Verification and observed results:
- Limitations or blockers:
- Next steps:
- Commit or release reference (when available):
