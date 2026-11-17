# Data sources and provenance

1. [Synthea downloads](https://synthetichealth.github.io/downloads.html): public April 2020, 1K sample CSV archive. Generated synthetic records, not real Medicaid beneficiaries. [Dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary). Cite Walonoski et al., JAMIA 2018, https://doi.org/10.1093/jamia/ocx079. Archive hash recorded in reports/data_provenance.json. Historical sample chosen for reproducible documented column layout; current CSV layouts differ.
2. [CMS Child Core Set](https://www.medicaid.gov/medicaid/quality-of-care/performance-measurement/adult-and-child-health-care-quality-measures/childrens-health-care-quality-measures): public state-level quality measures for Medicaid/CHIP context. Not downloaded or used as patient-level training observations. Aggregate measures cannot supply patient labels or validate individual predictions; reporting years and care years differ.
3. [CMS TAF](https://www.medicaid.gov/medicaid/data-systems/macbis/medicaid-chip-research-files/transformed-medicaid-statistical-information-system-t-msis-analytic-files-taf): controlled research files. Not downloaded or used. Requires approved request and DUA.

## Input dictionary

| Table | Used columns | Purpose |
|---|---|---|
| patients | Id, BIRTHDATE, DEATHDATE, GENDER, RACE | age, survival eligibility; audit attributes |
| payer_transitions | PATIENT, START_YEAR, END_YEAR, PAYER | synthetic Medicaid coverage proxy |
| payers | Id, NAME | identify Medicaid payer |
| encounters | Id, PATIENT, START, ENCOUNTERCLASS | history counts and 90-day ED labels |

Dates parsed consistently without timezone after UTC conversion. Duplicate patient/encounter IDs fail validation. Costs and synthetic names/contact identifiers are not used. Encounters are not adjudicated claims; real claims would need claim-line aggregation, reversals, runout, coding validation and enrollment-quality assessment.
