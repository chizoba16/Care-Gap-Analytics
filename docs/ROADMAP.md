# Development and evidence roadmap

## Current project direction

The platform covers both pediatric and adult Medicaid populations in NY, NJ, MD, VA and PA. Start with public data acquisition, a common state-aware data schema, quality assessment, and age-appropriate population measures. Develop all five modules defined in the [project scope](planning/PROJECT_SCOPE.md). Expand to longitudinal individual-level analysis when authorized data are available.

**Milestone 1 status — in progress:** CMS quality and enrollment acquisition and SQLite database foundation complete ([documentation](PUBLIC_DATA_FOUNDATION.md)). Next acquire and profile expenditure, provider and hospital datasets. Five-state expenditure and utilization analyses are pending.

## Existing pediatric prototype development steps

1. Obtain a larger pediatric synthetic cohort with documented Medicaid coverage; freeze generator version, configuration and seed. Do not broaden payer eligibility solely to make the model train.
2. Add a current Synthea date-based enrollment adapter; validate mappings. Add attrition counts, finer data-quality checks and explicit dataset observation end.
3. Implement clinically reviewed, version-specific well-care measures and licensed value sets where needed. Add infant-specific logic separately.
4. Complete validation-based model selection/calibration, bootstrap intervals and demographic audit. Keep the test set untouched until the protocol is frozen.
5. Obtain an institutional partner, IRB/privacy documentation, funding and CMS approval for TAF. Build a separate secure TAF adapter; public raw-table inputs are not TAF-ready.
6. Validate retrospectively across selected states and years after DQ Atlas review.
7. Pilot clinician-reviewed outreach and evaluate care-gap closure and follow-up. Estimate utilization changes with a credible comparison group; report costs, uncertainty and potential harms.
8. Maintain dated commits, protocols, partner contributions, evaluation results and publications. These document the endeavor's actual progress; code or synthetic accuracy alone does not demonstrate healthcare impact or NIW eligibility.
