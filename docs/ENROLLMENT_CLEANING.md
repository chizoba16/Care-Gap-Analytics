# Data engineering lab 01 — Medicaid enrollment profiling, cleaning and validation

## Goal

Create a Silver-layer table with one final CMS enrollment report per state and reporting month, using our actual five-state public data. This is a reproducible learning exercise and production pipeline increment. Bronze is the previously acquired source JSON and CSV; neither is modified. Silver is the validated CSV and typed Parquet. Gold metrics and predictive models follow separately.

### 1. Profile before changing data

From the repository root, open a Python interpreter or notebook and run:

```python
import pandas as pd

df = pd.read_csv('data/processed/cms_enrollment_five_states.csv', dtype=str, keep_default_na=False)
print(df.shape)
print(df.dtypes)
print(df.groupby(['cga_state', 'final_report']).size())
print(df.eq('').sum())
print(df.duplicated().sum())
```

Reading as strings preserves source formatting and blanks before we explicitly convert fields. Observed shape: 1,100 rows, 45 columns, and zero exact duplicate rows. A duplicate state-month is not automatically an erroneous record: CMS publishes preliminary and final versions.

### 2. Define the grain and select the correct version

The source grain is state × month × report version. The Silver grain is state × month, final version only. Filter `final_report == 'Y'`; retain preliminary records in Bronze. There are 545 matched final/preliminary pairs; 477 combined enrollment counts changed between releases. For New York in June 2017, the preliminary count was 6,071,815; the final count was 6,073,176. Five July 2026 rows are preliminary-only and are excluded until final versions are available.

### 3. Standardize values and preserve missingness

Use strict numeric parsing for the five enrollment counts and nullable integer types. Convert `YYYYMM` to the first date of the reporting month. Retain source state names, report flags and five enrollment footnote fields. The Silver table is focused on enrollment; the other source operational fields remain available in Bronze.

```python
final = df[df['final_report'] == 'Y'].copy()
final['reporting_month'] = pd.to_datetime(final['reporting_period'], format='%Y%m')
final['total_medicaid_enrollment'] = pd.to_numeric(
    final['total_medicaid_enrollment'].replace('', pd.NA), errors='raise'
).astype('Int64')
```

| Field | Missing values among 550 final rows |
| --- | ---: |
| Medicaid enrollment | 5 |
| CHIP enrollment | 5 |
| Combined Medicaid and CHIP enrollment | 0 |
| Adult Medicaid enrollment | 430 |
| Child Medicaid and CHIP enrollment | 5 |

The adult count was unreported in many historical observations. Do not impute zero, interpolate absent months, or subtract the combined child Medicaid/CHIP estimate from Medicaid-only enrollment to make an adult count. The populations differ.

### 4. Validate using business rules

| Check | Result |
| --- | --- |
| State coverage and consistent state identifiers | Passed: all five states |
| Unique state-month-report version | Passed |
| Valid dates and source report flags | Passed |
| Counts are nonnegative whole numbers or missing | Passed |
| Medicaid + CHIP = combined count where all three exist | 545 passed, 5 not evaluable |
| Adult and child subgroup counts do not exceed their corresponding reported totals | Passed where comparable |
| Final state-month rows | 550, 110 per state |
| Historical reporting gaps | 44 missing months per state, Oct 2013–May 2017; retained as gaps |
| Final reporting period | Sep 2013, then Jun 2017–Jun 2026 |

The pipeline fails before producing a clean table if required keys, numeric rules or financial-style reconciliation checks fail. Reporting gaps are tracked rather than treated as failures to repair. Review the source release before interpreting trends.

### 5. Execute and inspect

```sh
python clean_enrollment.py
python -m unittest discover -s tests -v
```

Outputs: `data/silver/cms_enrollment_clean.csv`, `data/silver/cms_enrollment_clean.parquet` (typed BIGINT counts and DATE month), and [`reports/enrollment_cleaning.json`](../reports/enrollment_cleaning.json). The report includes source and output checksums, null counts, per-state coverage, missing months and validation results. Raw data and Silver tables are ignored by Git; reproducible code and aggregate validation are tracked.

Try this SQL using DuckDB:

```sql
SELECT cga_state, count(*) AS final_months,
       count(total_adult_medicaid_enrollment) AS months_with_adult_counts
FROM read_parquet('data/silver/cms_enrollment_clean.parquet')
GROUP BY cga_state ORDER BY cga_state;
```

### Your exercises

1. Reproduce the raw row counts by state and report version. Explain why `drop_duplicates()` alone cannot choose the right version.
2. Calculate the percentage of final adult enrollment counts missing. Expected: 430 / 550 = 78.18%.
3. Verify the arithmetic check for each of the 545 complete rows. Explain why five rows cannot be checked.
4. List the preliminary-only months; explain why they cannot be included in a final-only trend.
5. Verify that the output contains 550 distinct state-month keys and no preliminary reports.

## Next lab

Clean CMS Child and Adult Core Sets, retaining suppression reasons, measure direction, population and methodology. Validate the appropriate grain before joining with enrollment or expenditure data. No new model has been trained.
