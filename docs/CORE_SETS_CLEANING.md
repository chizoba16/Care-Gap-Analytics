# Lab 02 — CMS Child and Adult Core Sets

## Objective and source

Convert the actual [CMS 2024 Core Set release](https://data.medicaid.gov/dataset/a5023394-ab10-465b-bb4a-7de5ac98d90c) five-state extract into a typed, reproducible Silver table. This is population-level quality reporting, not patient claims. The program name is not an exact age filter: use the age and population embedded in each rate definition. Original source notes and comments remain available. No model is trained in this lab.

## Step 1 — Inspect Bronze before changing anything

```python
import pandas as pd
raw = pd.read_csv('data/processed/cms_quality_five_states.csv', dtype=str, keep_default_na=False)
print(raw.shape)
print(raw.state_rate.value_counts())
print(pd.crosstab(raw.cga_state, raw.reporting_program))
print(raw.eq('').sum())
```

Reading as strings prevents pandas from automatically interpreting the literal CMS code `NA` as generic missing data. The source has 1,142 rows, 21 columns and no blank state rates; 94 rates instead use meaningful codes. Never edit the source file.

| State | Child | Adult | Total |
|---|---:|---:|---:|
| NY | 148 | 65 | 213 |
| NJ | 88 | 63 | 151 |
| MD | 105 | 96 | 201 |
| VA | 200 | 39 | 239 |
| PA | 200 | 138 | 338 |
| Total | 741 | 401 | 1,142 |

Row counts reflect published measure variants, not beneficiary counts or care quality.

## Step 2 — Define the grain

A row represents one state, Core Set year, reporting program, measure abbreviation, rate definition, population and methodology. All seven fields form the composite key. A measure can have multiple age groups, follow-up windows, methodologies or Medicaid/CHIP populations; dropping duplicates by state and measure alone would destroy valid records. Validate unique keys before loading.

## Step 3 — Preserve missing-rate semantics

| Original value | Clean status | Rows | Numeric result |
|---|---|---:|---|
| Numeric | reported | 1,048 | Original numeric value |
| DS | suppressed | 37 | NULL |
| NPR | not_publicly_reported | 22 | NULL |
| NA | zero_denominator | 21 | NULL |
| # | small_denominator_or_survey_count | 14 | NULL |

CMS notes explain the precise suppression or reporting reason, including survey-specific thresholds for `#`. Keep `state_rate` as the original string and create `state_rate_numeric` and `state_rate_status` alongside it. A reported zero is a valid number, unlike a missing or suppressed rate. Do not infer suppressed values or fill them with the mean.

## Step 4 — Standardize types, units and direction

Convert year and state reporting count into integers; mean, median, quartiles and state rate into numeric columns. Add `rate_unit`: 1,098 percentage rows, 11 rates per 1,000 beneficiary months, 27 per 100,000 beneficiary months and 6 ratios. Only percentages have a 0–100 range check. Add `measure_direction`: 1,069 higher-is-better and 73 lower-is-better rows. CMS bottom/top quartiles follow performance: for lower-is-better measures the numeric bottom quartile is greater than or equal to the top quartile. Reversing them would misrepresent the published benchmarks. Retain `rate_used_in_calculating_state_mean_and_median` and use only compatible comparison cohorts.

## Step 5 — Run, load and verify

```bash
python -m pip install -r requirements.txt
python clean_core_sets.py
python -m unittest discover -s tests -v
```

Outputs: `data/silver/cms_core_sets_clean.csv` (portable), `data/silver/cms_core_sets_clean.parquet` (typed analytics), and [validation report](../reports/core_sets_cleaning.json) (audit evidence). The actual run preserved 1,142 of 1,142 rows, produced 25 columns, retained 94 numeric nulls, found zero duplicate composite keys, and verified full Parquet round-trip equality. All 12 repository tests passed, including five targeted Core Set tests. The report records hashes, coverage, null counts and schema.

## Step 6 — Practice SQL in DuckDB

```sql
SELECT cga_state, reporting_program, state_rate_status, COUNT(*) AS rows
FROM read_parquet('data/silver/cms_core_sets_clean.parquet')
GROUP BY ALL ORDER BY 1, 2, 3;
```

Exercises: (1) reproduce the status counts; (2) group by rate unit and explain why combining units is invalid; (3) filter adult rows to one exact measure, population, methodology and rate definition, then compare reported rates by state with their direction and notes visible; (4) intentionally duplicate a row in a test fixture and observe validation failure. Never modify the original CMS extract.

## What this enables and does not enable

The table supports population-level quality and care-gap signal exploration, including follow-up and screening measures where reported. It does not identify individual patients, estimate avoidable spending, establish causality, or supply longitudinal training labels. A difference from a benchmark is a signal for review, not a count of missing services. Do not average rates across overlapping populations or methodologies, infer denominators from state counts, or treat a Core Set year as the precise dates of service. Before Gold integration, select compatible measure variants, define denominators and reporting eligibility, and retain source caveats. Next lab: CMS-64 expenditure validation.
