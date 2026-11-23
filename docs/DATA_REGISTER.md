# Data source register

All entries below are planned unless explicitly marked otherwise. Confirm availability, terms, years and schema during acquisition. Existing synthetic pediatric evaluation is documented in `DATA_SOURCES.md` and `reports/`.

| Source | Intended analytical unit / coverage | Status |
| --- | --- | --- |
| [HHS Medicaid provider spending by HCPCS](https://opendata.hhs.gov/datasets/medicaid-provider-spending/) | Provider-procedure-month; public aggregate, age and state attribution limitations | Planned |
| [HHS Medicaid provider spending by NDC](https://opendata.hhs.gov/datasets/medicaid-provider-spending-ndc/) | Provider-drug-month; public aggregate | Planned |
| [NY SPARCS](https://health.data.ny.gov/d/sf4k-39ay) | New York hospital discharges; age groups and expected payer | Planned |
| [CMS Child and Adult Core Sets](https://www.medicaid.gov/medicaid/quality-of-care/performance-measurement/adult-and-child-health-care-quality-measures) | Published quality measures by state and reporting period | Planned |
| [CMS expenditure reports](https://www.medicaid.gov/medicaid/financial-management/state-budget-expenditure-reporting-for-medicaid-and-chip) | State program expenditure categories | Planned |
| [HRSA](https://data.hrsa.gov/) and [Census](https://data.census.gov/) | Geographic access and socioeconomic indicators | Planned |
| [TAF](https://www.medicaid.gov/medicaid/data-systems/macbis/medicaid-chip-research-files/transformed-medicaid-statistical-information-system-t-msis-analytic-files-taf) | Approved beneficiary-level enrollment and claims in five states | Access not secured |

For each acquired source, record the exact URL, retrieval date, publication version, reporting period, file size/checksum, schema, row counts, grain, state and age coverage, missingness, suppression rules, joins, license/data-use terms, transformations and known limitations. Record validation results and actual local storage location without committing restricted records.
