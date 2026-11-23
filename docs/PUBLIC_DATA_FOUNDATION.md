# Public data foundation — milestone 1, increment 1

## What has been acquired

On November 22, 2026 (New York time), the public CMS datastore was queried for NY, NJ, MD, VA and PA. Two real aggregate datasets were acquired and validated. The HHS spending extracts, CMS expenditure reports and hospital discharge datasets remain the next acquisition work; no five-state claims or spending model is trained yet.

| State | Quality rows (2024 Core Set) | Enrollment source rows | Final enrollment months |
| --- | ---: | ---: | ---: |
| New York | 213 | 220 | 110 |
| New Jersey | 151 | 220 | 110 |
| Maryland | 201 | 220 | 110 |
| Virginia | 239 | 220 | 110 |
| Pennsylvania | 338 | 220 | 110 |
| Total | 1,142 | 1,100 | 550 |

Quality rows comprise 741 Child Core Set and 401 Adult Core Set records, including separate population, methodology and rate-definition rows. A total of 1,048 rows have reported numeric rates. The 94 remaining observations are preserved with their original flags (37 DS, 22 NPR, 21 NA, 14 #). Use source notes for each flag and avoid treating any as zero. The source is the 2024 Core Set, not a longitudinal patient record. Multiple rate rows within a state must not be added or averaged without reviewing measure definitions and populations.

Enrollment source observations span September 2013 to July 2026; the final-report view has 110 unique state-month records per state, ending June 2026. Preliminary and final reports are preserved separately. The adult Medicaid count has substantial historical missingness (855 of 1,100 source rows are blank); the published child count includes Medicaid and CHIP. Those counts are not interchangeable with the project’s Medicaid-only age cohorts. Preserve footnotes and avoid unsupported rate denominators.

## How to reproduce

Run from the repository root using Python 3.11+ (standard library only):

```sh
python acquire_public_data.py
python acquire_public_data.py --offline
```

The first command retrieves each of the five states from both official CMS APIs, confirms the returned count matches the source count, validates state values, and retains the JSON response. The second rebuilds outputs from the same local snapshots without querying CMS. `--data-dir` and `--report` allow alternative locations.

| Local artifact | Contents |
| --- | --- |
| `data/raw/cms/` | Ten exact official JSON responses |
| `data/processed/cms_quality_five_states.csv` | All in-scope quality rows, original schema plus `cga_state` |
| `data/processed/cms_enrollment_five_states.csv` | All in-scope enrollment reporting versions |
| `data/processed/cga_public.sqlite` | Queryable SQLite database with source tables and two curated views |
| `reports/public_data_acquisition.json` | Source URLs, actual snapshot hashes, schema descriptions, coverage, missingness and verification |

Raw and processed data are ignored by Git; the acquisition code and summary report are tracked. Source snapshots can be rebuilt locally. Current public releases can change, so compare retrieval hashes before claiming an identical rerun across fresh downloads.

## Data dictionary and analytical grain

The full source field descriptions are retained in the JSON report. Important fields are summarized below.

| Field | Meaning and use |
| --- | --- |
| `cga_state` | Standard two-letter state code from the verified source response |
| `core_set_year` | CMS reporting year, not necessarily the calendar year of service |
| `reporting_program` | Child or Adult Core Set, not an inferred individual age |
| `measure_abbreviation`, `rate_definition` | Measure code and specific rate indicator |
| `population`, `methodology` | Reporting cohort and calculation method; retain when comparing states |
| `state_rate`, `notes`, `statespecific_comments` | Reported value or status flag and caveats; source units vary by measure |
| `reporting_period` | Enrollment month as YYYYMM |
| `final_report`, `preliminary_or_updated` | CMS revision markers; select final reports for trend analyses |
| `total_medicaid_enrollment` | Published Medicaid enrollment count, subject to missingness and footnotes |
| `total_adult_medicaid_enrollment` | Published adult Medicaid enrollment count; substantial historical missingness |
| `medicaid_and_chip_child_enrollment` | Published child Medicaid and CHIP count |

All original source fields are stored as text in the first SQLite layer to preserve flags and reporting conventions. Cast only verified numeric values for specific analyses. `quality_reported` excludes the known nonnumeric rate flags; `enrollment_final` selects final reporting rows. Example query (counts records, not beneficiaries):

```sql
SELECT cga_state, reporting_program, COUNT(*) AS reported_measure_rows
FROM quality_reported
GROUP BY cga_state, reporting_program;
```

## Validation and next steps

The local SQLite integrity check returned `ok`; both source tables cover all five states; final enrollment state/month keys are unique. The existing pediatric unit tests passed (3 tests). No training or clinical validation was attempted. Next, acquire expenditure and provider spending data, establish their geographic attribution and coverage, then implement comparable quality and expenditure measures for the first analytical modules.
