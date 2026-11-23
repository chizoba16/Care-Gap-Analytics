# Spending data acquisition — milestone 1, increment 2

Acquired and verified on November 23, 2026 (New York time). These are public government releases; no restricted beneficiary-level TAF records have been obtained.

## Download sources

| Source | Date/period | Direct official download |
| --- | --- | --- |
| CMS-64 Financial Management Reports | FY 2018–2025 | [CMS archive index](https://www.medicaid.gov/medicaid/financial-management/state-budget-expenditure-reporting-for-medicaid-and-chip/expenditure-reports-mbes/cbes) |
| HHS Medicaid Provider Spending by HCPCS | Jan 2018–Dec 2024; Feb 9, 2026 release | [Parquet (3.07 GB)](https://stopendataprod.blob.core.windows.net/datasets/medicaid-provider-spending/2026-02-09/dataset/medicaid-provider-spending.parquet) / [CSV ZIP (3.76 GB)](https://stopendataprod.blob.core.windows.net/datasets/medicaid-provider-spending/2026-02-09/dataset/medicaid-provider-spending.csv.zip) |
| HHS Medicaid Provider Spending by NDC | Jan 2018–Dec 2024; Jul 24, 2026 release | [Parquet (234.6 MB)](https://stopendataprod.blob.core.windows.net/datasets/medicaid-provider-spending-ndc/2026-07-24/dataset/medicaid-provider-spending-ndc.parquet) / [CSV ZIP (321.2 MB)](https://stopendataprod.blob.core.windows.net/datasets/medicaid-provider-spending-ndc/2026-07-24/dataset/medicaid-provider-spending-ndc.csv.zip) |

The HHS metadata and interpretation are available on the [HCPCS release page](https://opendata.hhs.gov/datasets/medicaid-provider-spending/) and [NDC release page](https://opendata.hhs.gov/datasets/medicaid-provider-spending-ndc/). The project downloaded the Parquet versions, validated both published byte lengths and SHA-256 hashes, and checked Parquet header/footer signatures. The CSV links are alternative official formats.

## Reproduce the acquisition

```sh
pip install -r requirements.txt
python acquire_spending_data.py
python acquire_spending_data.py --offline --bundle ../CMS64_Five_State_Expenditure_2018_2025.zip
```

Use `--cms-only` if only the smaller CMS archives are needed. The pipeline preserves official files under `data/raw/`, validates them, and produces the CSV detail and reported totals under `data/processed/`. Raw data and the full download bundle stay outside Git history. The tracked [acquisition report](../reports/spending_data_acquisition.json) contains URLs, byte lengths, checksums and coverage.

## CMS-64 five-state extraction

Eight national ZIP archives were validated using ZIP CRC checks. Each includes the original CHIP and Medicaid financial workbooks. For NY, NJ, MD, VA and PA, the Medicaid workbook's Medical Assistance Program (`MAP`) and Administration (`ADM`) worksheets were extracted for every fiscal year. The result is 12,595 numeric source line items, including adjustments and subtotals, and 80 exact `Total Net Expenditures` lines (5 states × 8 years × 2 worksheets). Each reported total reconciles with federal plus state shares; all state-year-program keys are unique.

| Field | Meaning |
| --- | --- |
| `fiscal_year`, `state` | Federal fiscal year and state from workbook/sheet |
| `program` | `medical_assistance` or `administration` worksheet |
| `source_category`, `source_row` | Original CMS line label and Excel row number |
| `total_computable_usd` | Published total computable amount in USD |
| `federal_share_usd`, `state_share_usd` | Published federal and state shares in USD |
| `source_workbook`, `source_sheet` | Traceable source location |

**Important interpretation:** these are fiscal-year reporting amounts, not individual costs. The detail file contains subtotals, overlapping categories and negative adjustments; never sum all detail rows. The totals file extracts the exact line named `Total Net Expenditures` and should be interpreted in the context of its worksheet, not as a comprehensive Medicaid/CHIP grand total. Other source sections such as expansion CHIP are retained in source workbooks. Age-specific expenditures cannot be inferred from this file.

## HHS provider spending scope and next steps

HCPCS records are aggregates of billing provider, servicing provider, procedure and claim month. NDC records aggregate billing provider, prescribing provider, drug code and claim month. They include claim-line counts, beneficiary counts and line-level paid amounts. Both releases are national, with small-cell suppression and no beneficiary age or residence field. Provider-location linkage is a future, limited geographic proxy; it does not establish beneficiary state. Do not add unique beneficiary counts across overlapping cells or combine these payments with CMS-64 capitation as though they were independent spending totals.

The NDC release explicitly warns that repeated-digit placeholders can dominate unfiltered paid amounts, so validated product-level filtering is required before estimating pharmacy expenditures. Preserve all original data and investigate those records separately. The 2024 T-MSIS release data may be preliminary.

Next: profile the Parquet schemas and coverage with an efficient analytical engine; acquire provider geographic reference data; document the feasible state mapping; load the five-state CMS financial outputs into the analytical database; acquire comparable hospital data. No prediction model or waste estimate is reported at this acquisition milestone.
