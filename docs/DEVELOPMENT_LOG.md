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

## Entry template

- Date and milestone:
- Objective:
- Work completed and files changed:
- Data sources or decisions:
- Verification and observed results:
- Limitations or blockers:
- Next steps:
- Commit or release reference (when available):
