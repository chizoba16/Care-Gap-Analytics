# Model card — version 0.1

Status: pipeline implemented; public sample insufficient for training. No fitted model released.

Intended use: reproducible method development on synthetic data, then approved retrospective research. Event predicted: any emergency encounter within 90 days, not preventability or inappropriate utilization. Missing wellness flag is a record-based proxy requiring clinical review. Under-one children excluded by the full-history requirement.

Not intended for diagnosis, treatment, eligibility decisions, benefit denial or automated utilization restrictions. No performance, savings, fairness or national impact claim is supported by this release.

Validation plan: fit development models on earlier dates; tune and calibrate using validation only; freeze specification before later held-out testing. Evaluate prevalence and naive baseline, PR-AUC, discrimination, calibration, capacity-based recall and precision. Conduct subgroup audits with uncertainty estimates and adequate counts for age, sex, race/ethnicity, geography and disability status where permitted. Review false positives and missed gaps with clinicians. External-state validation and prospective outreach evaluation are required.

Privacy: raw data ignored by Git; no patient-level results published. Real CMS data and model artifacts must remain in the approved environment unless explicitly cleared for release under the DUA. Code can be public; data and output release are separate decisions.
