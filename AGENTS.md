# Care Gap Analytics — development instructions

## Project scope

Research platform covering Medicaid beneficiaries ages 0–17 and 18+ in NY, NJ, MD, VA and PA. Follow `docs/planning/PROJECT_SCOPE.md`. Develop the five analytical modules on a shared, reproducible data foundation. Public-data phase first; individual longitudinal analyses require approved data. Existing pediatric prototype behavior must remain reproducible.

## Documentation for every milestone

- Update `docs/DEVELOPMENT_LOG.md` with the actual work completed, decisions, changed files, verification, unresolved issues and next steps. Date entries; never backfill fictional work or results.
- Register each data source, version, access method, geography, population, grain, coverage, restrictions and checksum where feasible in `docs/DATA_REGISTER.md`. Distinguish unavailable, planned, acquired and validated states.
- Document definitions, eligibility, exclusions and denominators for every new care-gap or utilization measure. Label exploratory proxies and explain data limitations.
- Record material architecture or methodology decisions in `docs/DECISIONS.md`, including rationale and tradeoffs.
- Record model experiments, feature availability, splits, baselines, metrics, subgroup evaluation and limitations in `docs/EXPERIMENTS.md`. Update model cards when training or evaluation changes. Keep held-out outcomes independent of model selection.
- Include run commands and meaningful validation for implementation changes. Update the roadmap and release notes as milestones are actually completed.
- Maintain user-facing descriptions and example questions consistent with supported capabilities. Clearly identify demonstrated results versus proposed work.
- Keep restricted patient-level data, credentials and private study materials outside public GitHub history. Publish only permitted code, public-data documentation and disclosure-approved results. Do not infer missing age, state or individual histories from aggregate records.

## Working practice

Use descriptive commits and reviewable branches. Before handing off, inspect changes, run relevant checks, update the documentation, and record limitations. Do not describe a model as trained, deployed or clinically validated until the corresponding evidence exists.
