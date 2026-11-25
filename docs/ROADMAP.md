# Development and evidence roadmap

## Current project direction

The platform covers both pediatric and adult Medicaid populations in NY, NJ, MD, VA and PA. Start with public data acquisition, a common state-aware data schema, quality assessment, and age-appropriate population measures. Develop all five modules defined in the [project scope](planning/PROJECT_SCOPE.md). Expand to longitudinal individual-level analysis when authorized data are available.

**Milestone 1 status — in progress:** CMS quality and enrollment acquisition and SQLite database foundation complete ([documentation](PUBLIC_DATA_FOUNDATION.md)); CMS-64 and HHS provider spending releases acquired and verified ([spending documentation](SPENDING_DATA_FOUNDATION.md)); provider enrollment, NY hospital discharges and five-state county context acquired ([context documentation](CONTEXT_DATA_FOUNDATION.md)). Next profile HHS, evaluate geographic attribution and integrate CMS financial and county data. Four states' discharge-level data and TAF access remain pending.

## Milestone 2 — data profiling, cleaning and validation (in progress)

1. CMS enrollment — completed: [lab and validation report](ENROLLMENT_CLEANING.md).
2. CMS Child and Adult Core Sets — completed: [lab and validation report](CORE_SETS_CLEANING.md).
3. CMS-64 expenditure — next: validate source category hierarchy and funding reconciliation.
4. HHS spending and provider enrollment — profile and validate code, temporal and geographic coverage.
5. SPARCS, Census ACS and HRSA — clean source-specific fields and assess analytic joins.
6. Integrate validated Silver tables and define Gold analytical measures.

## Existing pediatric prototype development steps

1. Obtain a larger pediatric synthetic cohort with documented Medicaid coverage; freeze generator version, configuration and seed. Do not broaden payer eligibility solely to make the model train.
2. Add a current Synthea date-based enrollment adapter; validate mappings. Add attrition counts, finer data-quality checks and explicit dataset observation end.
3. Implement clinically reviewed, version-specific well-care measures and licensed value sets where needed. Add infant-specific logic separately.
4. Complete validation-based model selection/calibration, bootstrap intervals and demographic audit. Keep the test set untouched until the protocol is frozen.
5. Obtain an institutional partner, IRB/privacy documentation, funding and CMS approval for TAF. Build a separate secure TAF adapter; public raw-table inputs are not TAF-ready.
6. Validate retrospectively across selected states and years after DQ Atlas review.
7. Pilot clinician-reviewed outreach and evaluate care-gap closure and follow-up. Estimate utilization changes with a credible comparison group; report costs, uncertainty and potential harms.
8. Maintain dated commits, protocols, partner contributions, evaluation results and publications. These document the endeavor's actual progress; code or synthetic accuracy alone does not demonstrate healthcare impact or NIW eligibility.
