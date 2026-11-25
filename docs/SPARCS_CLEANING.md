# Lab 05 — NY SPARCS 2024 hospital discharge cleaning

## Objective and source

Transform the actual [2024 NY SPARCS public inpatient discharge file](https://health.data.ny.gov/d/sf4k-39ay), filtered at acquisition to primary expected payer Medicaid, into Silver. The acquired snapshot contains 635,606 rows and 33 fields. The SHA-256 is verified against the [acquisition report](../reports/context_data_acquisition.json). One row is one published inpatient discharge, **not a unique patient**. New York refers to hospital location, not beneficiary residence. Four other states' comparable discharge records are still pending. The public source is de-identified; preserve its suppression and never attempt re-identification. Source catalog license: [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/); maintain attribution and applicable conditions.

## Step 1 — Profile the data as strings

```python
import duckdb
db = duckdb.connect()
source = 'data/raw/sparcs/sparcs_2024_medicaid_primary.csv'
db.execute(f"CREATE VIEW raw AS SELECT * FROM read_csv('{source}', all_varchar=true)")
print(db.sql('SELECT age_group, COUNT(*) FROM raw GROUP BY 1'))
print(db.sql('SELECT length_of_stay, COUNT(*) FROM raw GROUP BY 1'))
```

Using strings first preserves leading zeros in facility IDs, ZIP prefixes and classification codes. Blank values become SQL NULL. Confirm the exact 33-field schema and validate Medicaid primary expected payer and discharge year 2024. No beneficiary enrollment eligibility or actual reimbursement is inferred from expected payer.

## Step 2 — Preserve missingness and disclosure protection

| Source fields | Nulls | Treatment |
|---|---:|---|
| Facility ID, certificate, hospital county and service area (each) | 2,641 | Retain source redaction, flag `facility_redacted` |
| ZIP prefix | 15,938 | Keep null; distinguish out-of-state code `OOS` |
| CCSR procedure code/description (each) | 173,085 | Keep null, require both fields absent or both present |
| Secondary payer | 462,424 | Keep null, do not invent coverage |
| Tertiary payer | 578,241 | Keep null |
| Birth weight | 531,058 | Keep null; 56 additional `UNKN` tokens are unknown |

3,062 additional rows repeat all 33 published fields. Since there is no discharge identifier or patient identifier, identical records can be distinct discharges. Retain every row and report the repeated-field count. There is no defensible deduplication key. Geography redacted by the source stays redacted. See the [NY data dictionary](https://www.health.data.ny.gov/api/views/82xm-y6g8/files/7806ca81-7f38-4a9a-8a57-b5f94ae4fba7?download=true) for general SPARCS public data definitions; use the current dataset's CCSR field names.

## Step 3 — Standardize LOS and cohorts

Classify `0-17` as pediatric and the four remaining published age bands as adult: 159,975 pediatric and 475,631 adult discharges. Do not assign an exact age. Published stays range from 1 to 119 exact days plus the right-censored `120+` bucket (1,192 records). Create `stay_days_exact` (null for capped stays), `stay_days_lower_bound` (120 for capped stays), and `stay_right_censored` Boolean. A mean of lower bounds is a lower bound on the mean, not the exact mean for all stays. Keep source LOS string. Parse birth weight in grams without assuming unknown is zero.

## Step 4 — Validate money, codes and facility information

Convert charges and estimated hospital costs to exact DECIMAL(18,2) USD; validate their original precision and nonnegative format, including leading-decimal values such as `.05`. Keep all values, including zero and unusual costs. `cost_exceeds_charge`, `zero_estimated_cost`, and `high_estimated_cost_review` (at least $1 million estimated cost) support review, not automatic exclusion or fraud detection. Cost is a hospital estimate, not actual Medicaid payment; charge is not payment either. Do not compute savings or sum with CMS-64/HHS. Code format checks cover CCSR, APR DRG/MDC, ZIP prefix and facility IDs. Check severity code/text consistency and procedure code/description null pairing. These are structural checks, not clinical code-set or facility registry validation. Record `hospital_state=NY` and a Boolean ED indicator; the latter means a discharge with ED involvement, not all ED visits or repeated ED use.

## Step 5 — Run and validate

```bash
python -m pip install -r requirements.txt
python clean_sparcs.py
python -m unittest discover -s tests -v
```

Silver outputs under `data/silver/`: `sparcs_ny_2024_medicaid_clean.parquet` (record-level), `sparcs_ny_2024_medicaid_cohort_summary.csv` (two age cohorts). [Validation report](../reports/sparcs_cleaning.json) records source/output checksums, schema, observed nulls and validation failure counts. The Parquet output is checked by full multiset difference plus exact row count (so repeated records are preserved). No model trained or deployed.

**Observed outcome:** 635,606 records retained, 46 fields (33 source fields plus 13 derived fields), zero structural validation failures, 23 repository tests passed. Financial review flags: 17,744 estimated costs above charges, 338 estimated costs at least $1 million, two zero estimated costs and two zero charges. These are review signals, not evidence of inappropriate utilization.

| Cohort | Discharges | ED-involved discharges | 120+ day stays |
|---|---:|---:|---:|
| Adult | 475,631 | 311,837 | 878 |
| Pediatric | 159,975 | 43,135 | 314 |
| Total | 635,606 | 354,972 | 1,192 |

## Step 6 — Practice SQL

```sql
SELECT age_cohort, COUNT(*) AS discharges,
       COUNT(*) FILTER (WHERE ed_indicator) AS ed_involved_discharges,
       AVG(total_costs) AS estimated_cost_per_discharge,
       AVG(stay_days_lower_bound) AS mean_stay_lower_bound
FROM read_parquet('data/silver/sparcs_ny_2024_medicaid_clean.parquet')
GROUP BY 1;
```

Exercises: compare the two cohorts and distinguish discharge count from patient count; count `120+` by cohort, compare exact-stay mean with lower-bound mean; compare cost and charge and examine flagged records without inferring waste; check how many redacted facilities cannot be used in geographic comparisons. Do not reverse withheld geography or infer unique persons. Use aggregated outputs and preserve disclosure rules in beta reports.

## Research limitations and next steps

Use as a New York inpatient sub-study. Public records lack linked longitudinal patient IDs and precise service dates; cannot calculate patient-level 30-day readmissions, future ED risk, or individual care gaps. Cost prediction can be investigated later with a defined prediction time and only information available at that time; discharge diagnosis, LOS, severity and disposition may cause leakage if predicting before admission/discharge. Hospital county is distinct from patient's residence and ZIP prefix cannot be assumed to identify county. Avoid age-specific Medicaid expenditure claims or interpreting discharge counts as utilization rates without compatible denominators. Next lab: Census ACS and HRSA county context; then validated Gold integration.
