# Lab 03 — CMS-64 Medicaid expenditure cleaning

## Objective

Use the actual FY 2018–2025 CMS Financial Management Reports for New York, New Jersey, Maryland, Virginia and Pennsylvania to create reproducible financial Silver tables. Source: [CMS expenditure reports](https://www.medicaid.gov/medicaid/financial-management/state-budget-expenditure-reporting-for-medicaid-and-chip/expenditure-reports-mbes/cbes). Both input CSV hashes matched the prior [acquisition report](../reports/spending_data_acquisition.json). These Medicaid workbook reports contain program-level financial amounts, not age-specific claims or individual payments. Retain separate MAP (medical assistance) and ADM (administration) scopes.

## Step 1 — Profile the input

```python
import pandas as pd
raw = pd.read_csv('data/processed/cms64_five_state_detail.csv', dtype=str, keep_default_na=False)
print(raw.shape)
print(raw.eq('').sum())
print(raw.groupby(['fiscal_year', 'program']).size())
print(raw.duplicated(['state', 'fiscal_year', 'program', 'source_category']).sum())
```

Observed: 12,595 rows, 10 columns, 335 distinct source labels, no blank required fields. The category-based key has 115 extra repeated rows. Do not delete these: a label can occur in different sections of the same sheet. Instead use `(state, fiscal_year, program, source_row)` as the line key and `(state, fiscal_year, program)` as the totals key. Keep workbook, sheet, row and original label for traceability. Expect 5 states × 8 years × 2 programs = 80 worksheets.

## Step 2 — Validate money types and funding

The source amounts are exact signed whole USD dollars, not cents. Convert them to signed 64-bit integers rather than binary floating-point numbers. Every line must satisfy `total_computable_usd = federal_share_usd + state_share_usd`. There are 432 negative total amounts and 8,220 zero totals. Negative amounts may reflect rebates, recoveries or adjustments; zero is a reported value, not missing. Preserve both. No currency conversion, inflation adjustment or imputation is performed.

## Step 3 — Distinguish detail from subtotals

Inspect original Excel row ordering for each worksheet; the positions change by year. The pipeline locates the exact `Balance` and `Total Net Expenditures` labels separately within each sheet and validates the arithmetic of the preceding and intervening lines. Preserve all later sections without claiming they are additive or fully mapping their internal hierarchies.

| `line_role` | Rows | Include in main net sum? |
|---|---:|---|
| main_balance_component | 6,230 | Yes |
| main_net_adjustment | 140 | Yes |
| main_balance_subtotal | 80 | No |
| main_reported_net_total | 80 | No; use independently as the authoritative reported measure |
| outside_main_net_total | 6,065 | No; further source-specific interpretation required |

For all 80 sheets and each of the three funding columns, verify the sum of components before Balance equals Balance; then Balance plus all lines between it and Total Net Expenditures equals the exact reported net total. The latter includes Collections and other worksheet adjustments. Cross-check the selected net lines against the separate acquisition totals file. The `include_in_main_net_sum` Boolean exposes the verified additive subset. Never sum every line: this mixes components, subtotals and later sections such as Title VIII, CHIP-related, COVID and other reporting lines. Neither the main net line nor the later sections alone should be labeled comprehensive Medicaid/CHIP spending.

## Step 4 — Run the ETL and validate

```bash
python -m pip install -r requirements.txt
python clean_cms64.py
python -m unittest discover -s tests -v
```

Outputs under `data/silver/`: `cms64_detail_clean.csv` and `.parquet` (12,595 rows, 12 fields), and `cms64_reported_totals_clean.csv` and `.parquet` (80 rows, 11 fields). See [audit report](../reports/cms64_cleaning.json) for hashes and Parquet schemas. All rows retained, all 12,595 funding splits reconciled, all 80 balance and net computations reconciled, all 80 totals matched the original extract, and both Parquet round trips passed full equality. All 18 repository tests passed, including six new CMS-64 tests.

## Step 5 — Practice SQL

```sql
SELECT state, fiscal_year, program, total_computable_usd,
       federal_share_usd, state_share_usd
FROM read_parquet('data/silver/cms64_reported_totals_clean.parquet')
ORDER BY state, fiscal_year, program;
```

```sql
SELECT state, fiscal_year, program,
       SUM(total_computable_usd) AS reconstructed_main_net
FROM read_parquet('data/silver/cms64_detail_clean.parquet')
WHERE include_in_main_net_sum
GROUP BY ALL;
```

Exercises: compare these two result sets by the total key; find negative rebate/collection lines without discarding them; quantify the difference if every detail row is summed (a deliberately incorrect diagnostic); graph one program's nominal reported net amount by fiscal year for a single state. Explain why fiscal-year amounts should not be casually joined to calendar-year enrollment, and why the denominator for per-enrollee spending must cover comparable program/payer populations and reporting months.

## Limits and next step

The validated totals support historical spending comparisons and potential forecast development. Eight annual observations per state/program are a small series; require defensible temporal validation and baseline comparisons. Do not infer age-specific expenditure, claim utilization counts, fraud, waste, causality or cost savings from these financial reports. Managed-care payments and provider claims are different measurement bases and are not additive. No model has been trained. Next: HHS provider spending and provider enrollment profiling, with explicit geographic and population limitations.
