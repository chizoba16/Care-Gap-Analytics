# Provider enrollment, hospital and county context acquisition

Milestone 1, increment 3 — November 23, 2026 (New York time). All releases below are real public records or published survey estimates. No restricted TAF records were acquired.

## Acquired sources

| Source | Release and coverage | Official access |
| --- | --- | --- |
| HHS Medicaid Provider Enrollment Segments | July 24, 2026 release, segments overlapping 2018–2024; national | [Release](https://opendata.hhs.gov/datasets/medicaid-provider-enrollment-segments/) / [Parquet](https://stopendataprod.blob.core.windows.net/datasets/medicaid-provider-enrollment-segments/2026-07-24/dataset/medicaid-provider-enrollment-segments.parquet) |
| NY SPARCS de-identified inpatient discharges | 2024; NY facilities; first expected payer Medicaid | [Data portal](https://health.data.ny.gov/d/sf4k-39ay) |
| HRSA Area Health Resources Files | 2024–2025 county release; national source, five-state extraction | [CSV ZIP](https://data.hrsa.gov/DataDownload/AHRF/AHRF_2024-2025_CSV.zip) / [technical documentation](https://data.hrsa.gov/DataDownload/AHRF/AHRF_USER_TECH_2024-2025.zip) |
| Census ACS five-year detailed tables | 2020–2024 estimates, five-state counties | [Bulk summary files](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/) |

## Observed coverage

| State | Provider enrollment segments | Matched ACS/HRSA county-equivalents |
| --- | ---: | ---: |
| NY | 323,566 | 62 |
| NJ | 221,172 | 21 |
| MD | 1,524,148 | 24 |
| VA | 683,652 | 133 |
| PA | 896,019 | 67 |
| Total | 3,648,557 | 307 |

The national provider source has 65,970,112 segments. The five-state extract retains every source row whose `STATE_CD` is in scope; it includes Medicaid and CHIP plans and potentially inactive status segments. A provider can have multiple segments and multiple state enrollments. These counts are not unique providers or beneficiaries.

The NY hospital file contains 635,606 discharges, matching the official API count for 2024 first expected payer Medicaid. Of these, 159,975 are ages 0–17 and 475,631 are ages 18 and older. Each row is a discharge, not a unique patient. Expected payer, hospital location and estimated hospital costs are separate from confirmed Medicaid enrollment, residence and actual payment.

## Reproduce and download

```sh
pip install -r requirements.txt
python acquire_context_data.py
python acquire_context_data.py --offline --bundle ../CGA_Provider_and_County_Data.zip --hospital-bundle ../CGA_NY_SPARCS_2024_Medicaid.zip
```

The Census API required a key; the script instead uses the official 2024 table-based summary files without requiring credentials. It extracts standard county geographic IDs and preserves paired estimates and margins of error. Local output paths:

| Artifact | Path |
| --- | --- |
| Provider enrollment five-state Parquet | `data/processed/provider_enrollment_five_states.parquet` |
| HRSA county CSV (4,352 source columns) | `data/processed/ahrf_2024_2025_five_states.csv` |
| ACS county CSV | `data/processed/acs_2020_2024_five_states.csv` |
| NY hospital discharge CSV | `data/raw/sparcs/sparcs_2024_medicaid_primary.csv` |
| Provenance and quality report | `reports/context_data_acquisition.json` |

Raw data stays outside Git history. The bundles include source attribution and provenance. SPARCS is an ODbL catalog release; observe applicable attribution, privacy and redistribution terms. Preserve original source data and revisions; the report records file hashes. The SPARCS count assertion describes the observed release; review any future refresh that changes the count.

## Key analytical fields

| Source field | Definition |
| --- | --- |
| `NPI`, `STATE_CD` | Provider identifier and submitting-state enrollment code, not beneficiary residence or payer claim state |
| `ENRL_START_DT`, `ENRL_END_DT` | Provider enrollment segment dates; use temporal overlap when profiling and joining |
| `ENRL_STATUS_CD`, `ENRL_PLAN_CD`, `PRVDR_TYPE` | Enrollment status, plan, provider type; source descriptions preserved |
| `fips_st_cnty` / `county_fips` | Five-character county-equivalent FIPS; preserve leading zeros |
| `B01003_E001` | ACS total resident population estimate |
| `B17001_E001`, `B17001_E002` | Population for whom poverty status is determined; population below poverty |
| `B19013_E001` | Median household income estimate, inflation-adjusted dollars |
| `B08201_E001`, `B08201_E002` | Households; households with no vehicles available |
| ACS `M` fields | Published margins of error corresponding to the estimate fields |
| SPARCS `age_group`, `payment_typology_1`, `discharge_year` | Admission age group, primary expected payer and discharge year |
| SPARCS `hospital_county`, `total_charges`, `total_costs` | Facility geography, charges and estimated cost; not Medicaid reimbursement |

County-level context applies to the general population; avoid attributing census estimates to individuals or claiming each is a Medicaid member. HRSA includes multiple reference years in its 4,352 columns; select variables only after reviewing the technical documentation. ACS sentinel values and missingness must be handled before computing rates.

## Hospital coverage still outstanding

NY is the only acquired discharge-level source. Comparable state files require external access arrangements: [NJ discharge system/HCUP](https://nj.gov/health/healthcarequality/health-care-professionals/njddcs/), [Maryland HSCRC application](https://hscrc.maryland.gov/pages/hsp-data-request.aspx), [Virginia VHI](https://www.vhi.org/data/hospital-discharge-data/), [Pennsylvania PHC4 purchase](https://www.phc4.org/request-custom-data/available-data/). Explore [HCUP Fast Stats](https://datatools.ahrq.gov/hcup-fast-stats/) for aggregate cross-state comparisons subject to its applicable data use agreement and actual state coverage. Do not claim five-state discharge-level coverage until obtained. TAF access remains pending.

## Next steps

Profile spending schemas, perform a conservative month-aware provider enrollment linkage with ambiguity flags, and integrate CMS financial and county tables into the shared database. Use public claims aggregates only for supported provider-level analyses; avoid attributing spending to patient states through provider enrollment alone. No model training or individual care-gap measurement was performed in this increment.
