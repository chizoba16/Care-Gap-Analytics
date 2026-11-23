# Care Gap Analytics: child and adult Medicaid project scope

The project targets Medicaid beneficiaries of all ages across five states: New York (NY), New Jersey (NJ), Maryland (MD), Virginia (VA), and Pennsylvania (PA). Children ages 0–17 and adults ages 18 and older will be analyzed using age-appropriate measures and independently evaluated predictive models where data support them. The existing pediatric prototype provides an initial foundation. Public real-world data will be used first, followed by approved longitudinal Medicaid records when available.

## Five-state dataset scope

Build a common data pipeline for NY, NJ, MD, VA and PA, with a state field, reporting period, age group, payer/program and source provenance where available. Assess data quality and coverage by state and period. Public national claims aggregates may include Medicaid and CHIP and lack beneficiary ages or residence; label those limitations explicitly. New York SPARCS is a New York discharge-level source, so comparable discharge-level data for other states must be obtained separately. Never imply five-state or age-specific coverage for a dataset that does not provide it.

Use child and adult CMS Core Set indicators as applicable. Age-specific eligibility, exclusions, enrollment and observation windows will be documented before individual-level measurement. Assess children and adults separately, and distinguish dual eligibility where supported.

## Five analytical modules

1. Care gap detection: reported population quality measures initially; individual gaps after authorized longitudinal access.
2. Predictive utilization and spending: expenditure forecasts and discharge cost estimates initially; individual ED, hospitalization and readmission risk later.
3. Utilization efficiency: unusual cost and service-use patterns for review, with validated definitions and appropriate adjustment.
4. Resource allocation: population resource planning initially; authorized care coordination workflows later.
5. Population health analytics: comparable state and subgroup measures where data support them.

## First development milestone

Acquire the public HHS provider spending extracts, New York SPARCS and CMS quality and expenditure data. Document source versions, schemas, reporting periods, geographic limitations and data quality. Build reproducible ingestion and transformation pipelines before fitting models. Public Medicaid/CHIP aggregates cannot establish adult-only or individual longitudinal outcomes without supporting data.

## Planning documents

The research proposal (Version 2.0) and data strategy and beta user guide (Version 3.0) reflect the child-and-adult, five-state scope and documentation workflow. These planning documents are maintained separately outside public Git history.

The beta will present documented measures and model results, with data source, population, time period and limitations. Restricted records must remain in authorized environments. The research plan calls for validation and independent beta feedback before any claims of impact or savings.
