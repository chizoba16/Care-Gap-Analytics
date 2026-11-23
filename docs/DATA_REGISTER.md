# Data source register

All entries below are planned unless explicitly marked otherwise. Confirm availability, terms, years and schema during acquisition. Existing synthetic pediatric evaluation is documented in `DATA_SOURCES.md` and `reports/`.

| Source | Intended analytical unit / coverage | Status |
| --- | --- | --- |
| [HHS Medicaid provider spending by HCPCS](https://opendata.hhs.gov/datasets/medicaid-provider-spending/) | National provider-procedure-month; 2018–2024; age and state attribution limitations | Acquired; published SHA-256 verified |
| [HHS Medicaid provider spending by NDC](https://opendata.hhs.gov/datasets/medicaid-provider-spending-ndc/) | National provider-drug-month; 2018–2024 | Acquired; published SHA-256 verified |
| [HHS Medicaid Provider Enrollment Segments](https://opendata.hhs.gov/datasets/medicaid-provider-enrollment-segments/) | 2018–2024 enrollment segments; 3,648,557 rows across five states | Acquired; published hash and output state counts verified |
| [NY SPARCS](https://health.data.ny.gov/d/sf4k-39ay) | 2024 New York hospital discharges; primary expected Medicaid payer; 635,606 rows | Acquired; count and payer/year filters verified |
| NJ, MD, VA and PA hospital discharge records | Comparable individual discharge data | Access not secured; application/purchase sources identified |
| [CMS Child and Adult Core Sets](https://data.medicaid.gov/dataset/a5023394-ab10-465b-bb4a-7de5ac98d90c) | Published 2024 Core Set quality measures, 1,142 rows across all five states | Acquired; validated source counts and coverage |
| [CMS Medicaid and CHIP enrollment](https://data.medicaid.gov/dataset/6165f45b-ca93-5bb5-9d06-db29c692a360) | State-month enrollment reporting versions; 1,100 rows and 550 final reports across all five states | Acquired; validated source counts and final key uniqueness |
| [CMS expenditure reports](https://www.medicaid.gov/medicaid/financial-management/state-budget-expenditure-reporting-for-medicaid-and-chip) | State program expenditure line items FY 2018–2025; 12,595 five-state rows and 80 reported totals | Acquired; ZIP integrity and funding reconciliation passed |
| [HRSA AHRF](https://data.hrsa.gov/data/download) | 2024–2025 county file; 307 in-scope county-equivalents, 4,352 fields | Acquired; ZIP and unique county keys verified |
| [Census ACS](https://www.census.gov/programs-surveys/acs/data/summary-file.2024.html) | 2020–2024 five-year estimates, four detailed tables, 307 county-equivalents | Acquired; exact county key match to HRSA |
| [TAF](https://www.medicaid.gov/medicaid/data-systems/macbis/medicaid-chip-research-files/transformed-medicaid-statistical-information-system-t-msis-analytic-files-taf) | Approved beneficiary-level enrollment and claims in five states | Access not secured |

For each acquired source, record the exact URL, retrieval date, publication version, reporting period, file size/checksum, schema, row counts, grain, state and age coverage, missingness, suppression rules, joins, license/data-use terms, transformations and known limitations. Record validation results and actual local storage location without committing restricted records.

See [public data foundation](PUBLIC_DATA_FOUNDATION.md) and [acquisition report](../reports/public_data_acquisition.json) for actual URLs, data dictionary, source snapshots, provenance and verification. These CMS datasets are public aggregate disclosures; retain source attribution and suppression. Review applicable data terms before redistribution.

See [spending data foundation](SPENDING_DATA_FOUNDATION.md) for expenditure download URLs, data dictionary, scope and interpretation, and [spending acquisition report](../reports/spending_data_acquisition.json) for checksums and observed coverage.

See [context data foundation](CONTEXT_DATA_FOUNDATION.md) for source access, data dictionary, remaining hospital-state coverage and [acquisition report](../reports/context_data_acquisition.json) for source hashes and verification.
