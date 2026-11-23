# Care Gap Analytics

Research platform under development supporting improved coordination of Medicaid-funded healthcare for children (ages 0–17) and adults (ages 18+) in New York, New Jersey, Maryland, Virginia and Pennsylvania. The planned platform includes care gap detection, predictive utilization and spending, utilization efficiency, resource allocation, and population health analytics. See the [project scope](docs/planning/PROJECT_SCOPE.md) for the five-state data strategy and age-specific approach.

The current implemented prototype is pediatric: it identifies a missing-wellness-record proxy and provides a trainable 90-day emergency department utilization pipeline. It does not establish avoidable use, medical necessity, cost savings, or clinical effectiveness. The adult and five-state data pipelines and models are planned, pending acquisition and validation.

## Project documentation

- [Five-state project scope](docs/planning/PROJECT_SCOPE.md)
- [Development roadmap](docs/ROADMAP.md)
- [Development log](docs/DEVELOPMENT_LOG.md)
- [Data source register](docs/DATA_REGISTER.md)
- [Research and architecture decisions](docs/DECISIONS.md)
- [Model experiment register](docs/EXPERIMENTS.md)
- [Development instructions](AGENTS.md)
- [Public data foundation — acquisition and database](docs/PUBLIC_DATA_FOUNDATION.md)
- [Spending data foundation — official downloads and verified extraction](docs/SPENDING_DATA_FOUNDATION.md)

## Five-state public data foundation

The first acquisition increment has retrieved official CMS quality and enrollment data for all five states. Run `python acquire_public_data.py` to retrieve the current source release or `python acquire_public_data.py --offline` to rebuild from local snapshots. See the [acquisition report](reports/public_data_acquisition.json) for observed coverage and validation. The initial SQLite database is local under `data/processed/`.

## Current result

The public April 2020 Synthea sample contains only **3 eligible training observations and no validation/test observations** under the conservative coverage rules. Training is deliberately skipped. See [evaluation](reports/evaluation.json). No trained or validated model is claimed. A larger synthetic pediatric Medicaid cohort or approved research data is required.

## Run

Python 3.11 recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py --download
python -m unittest discover -s tests -v
```

The download reads four tables from the public Synthea archive. All patient-level source files stay local under ignored `data/raw/`. Only summary evaluation and provenance are tracked. Run without `--download` to reuse downloaded data. `--raw PATH` and `--reports PATH` override locations.

## Design

- Population: simulated Medicaid beneficiaries aged 0–17; full 365-day pre-index history means infants under one are excluded in version 0.1.
- Enrollment: payer named Medicaid; year-only transitions interpreted conservatively with exclusive END_YEAR. This is an enrollment proxy, not actual monthly eligibility.
- Windows: 365-day history `[index-365d, index)`; ED outcome `[index, index+90d)`; complete coverage proxy required across both.
- Development: 2017 training, 2018 validation, 2019 testing; deterministic patient hashing assigns disjoint individuals to 60/20/20 partitions. No future encounters enter features.
- Features: age and previous ED, inpatient, ambulatory and wellness encounter counts. Race/gender are retained only in memory for future audit development, not fitted.
- Models: prevalence baseline, scaled logistic regression, gradient boosting. Minimum training counts gate fitting. No model is automatically selected from test results.
- Metrics: average precision, ROC AUC, Brier score, mean predicted risk, precision/recall at 10% outreach capacity; age-group summaries suppressed when too small. Additional calibration curves and demographic audits are required before real-world use.
- Gap: ages 3–17 with no wellness encounter in history. This is **not an implemented CMS/HEDIS WCV measure**. No official code sets, exclusions, or clinical validation are supplied.

See [sources](docs/DATA_SOURCES.md), [model card](docs/MODEL_CARD.md), [research access guide](docs/RESEARCH_ACCESS.md), and [roadmap](docs/ROADMAP.md).
