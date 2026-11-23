# Data source register

All entries below are planned unless explicitly marked otherwise. Confirm availability, terms, years and schema during acquisition. Existing synthetic pediatric evaluation is documented in `DATA_SOURCES.md` and `reports/`.

| Source | Intended analytical unit / coverage | Status |
| --- | --- | --- |
| [HHS Medicaid provider spending by HCPCS](https://opendata.hhs.gov/datasets/medicaid-provider-spending/) | Provider-procedure-month; public aggregate, age and state attribution limitations | Planned |
| [HHS Medicaid provider spending by NDC](https://opendata.hhs.gov/datasets/medicaid-provider-spending-ndc/) | Provider-drug-month; public aggregate | Planned |
| [NY SPARCS](https://health.data.ny.gov/d/sf4k-39ay) | New York hospital discharges; age groups and expected payer | Planned |
| [CMS Child and Adult Core Sets](https://data.medicaid.gov/dataset/a5023394-ab10-465b-bb4a-7de5ac98d90c) | Published 2024 Core Set quality measures, 1,142 rows across all five states | Acquired; validated source counts and coverage |
| [CMS Medicaid and CHIP enrollment](https://data.medicaid.gov/dataset/6165f45b-ca93-5bb5-9d06-db29c692a360) | State-month enrollment reporting versions; 1,100 rows and 550 final reports across all five states | Acquired; validated source counts and final key uniqueness |
| [CMS expenditure reports](https://www.medicaid.gov/medicaid/financial-management/state-budget-expenditure-reporting-for-medicaid-and-chip) | State program expenditure categories | Planned |
| [HRSA](https://data.hrsa.gov/) and [Census](https://data.census.gov/) | Geographic access and socioeconomic indicators | Planned |
| [TAF](https://www.medicaid.gov/medicaid/data-systems/macbis/medicaid-chip-research-files/transformed-medicaid-statistical-information-system-t-msis-analytic-files-taf) | Approved beneficiary-level enrollment and claims in five states | Access not secured |

For each acquired source, record the exact URL, retrieval date, publication version, reporting period, file size/checksum, schema, row counts, grain, state and age coverage, missingness, suppression rules, joins, license/data-use terms, transformations and known limitations. Record validation results and actual local storage location without committing restricted records.

See [public data foundation](PUBLIC_DATA_FOUNDATION.md) and [acquisition report](../reports/public_data_acquisition.json) for actual URLs, data dictionary, source snapshots, provenance and verification. These CMS datasets are public aggregate disclosures; retain source attribution and suppression. Review applicable data terms before redistribution.
