# Model experiment register

The existing pediatric prototype evaluation is recorded in `../reports/evaluation.json` and `MODEL_CARD.md`. Its public synthetic sample did not meet the minimum training requirements. No new model has been trained for the five-state scope.

For each future experiment, record:

| Field | Required evidence |
| --- | --- |
| Experiment identifier and date | Unique ID and execution date |
| Research question and outcome | Prediction target, horizon, population and intended use |
| Data | Source versions, eligibility, observation period, sample counts and exclusions |
| Reproducibility | Code commit, run command, dependencies and random seed |
| Features and splits | Feature availability at prediction time, leakage checks and train/validation/test dates |
| Baseline and model | Algorithms, hyperparameters and selection criteria |
| Results | Appropriate accuracy, uncertainty, calibration, subgroup and state results |
| Interpretation | Limitations, generalizability, fairness concerns and next decision |

Forecasts should be compared against a simple historical or seasonal baseline. Classification models should include discrimination, precision/recall and calibration. Record failed or skipped experiments as such.
