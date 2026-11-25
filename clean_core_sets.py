"""Clean the published five-state CMS Core Set quality snapshot without imputing rates."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from acquire_public_data import STATES
from clean_enrollment import digest

KEY = ['cga_state', 'core_set_year', 'reporting_program', 'measure_abbreviation',
       'rate_definition', 'population', 'methodology']
BENCHMARKS = ['mean', 'median', 'bottom_quartile', 'top_quartile']
FLAGS = {'DS': 'suppressed', 'NPR': 'not_publicly_reported', 'NA': 'zero_denominator',
         '#': 'small_denominator_or_survey_count'}
DIRECTION = {'Higher rates are better for this measure': 'higher_is_better',
             'Lower rates are better for this measure': 'lower_is_better'}
REQUIRED = KEY + BENCHMARKS + ['state', 'domain', 'measure_name', 'measure_type', 'state_rate',
            'number_of_states_reporting', 'notes', 'source', 'statespecific_comments',
            'rate_used_in_calculating_state_mean_and_median']


def numeric(values, field):
    if not values.str.fullmatch(r'\d+(?:\.\d+)?').all():
        raise ValueError(f'Invalid numeric value in {field}')
    return pd.to_numeric(values, errors='raise').astype('Float64')


def clean(raw):
    missing = set(REQUIRED) - set(raw.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    if set(raw.cga_state) != set(STATES) or not raw.cga_state.map(STATES).eq(raw.state).all():
        raise ValueError('State coverage or identifiers disagree')
    if raw[KEY].eq('').any().any() or raw.duplicated(KEY).any():
        raise ValueError('Missing or duplicate measure grain')
    if not raw.core_set_year.str.fullmatch(r'\d{4}').all():
        raise ValueError('Invalid Core Set year')
    if not raw.reporting_program.isin(['Adult Core Set', 'Child Core Set']).all():
        raise ValueError('Unknown program')
    if not raw.measure_type.isin(DIRECTION).all():
        raise ValueError('Unknown measure direction')
    if not raw.rate_used_in_calculating_state_mean_and_median.isin(['Yes', 'No']).all():
        raise ValueError('Unknown benchmark inclusion flag')

    silver = raw.copy()
    silver['core_set_year'] = raw.core_set_year.astype('int64')
    flagged = raw.state_rate.isin(FLAGS)
    if raw.loc[flagged, 'notes'].str.strip().eq('').any():
        raise ValueError('Missing explanation for nonnumeric rate')
    silver['state_rate_status'] = raw.state_rate.map(FLAGS).fillna('reported')
    silver['state_rate_numeric'] = numeric(raw.loc[~flagged, 'state_rate'], 'state_rate').reindex(raw.index)
    silver['measure_direction'] = raw.measure_type.map(DIRECTION)
    definitions = raw.rate_definition
    unit = pd.Series('unknown', index=raw.index)
    unit.loc[definitions.str.startswith('Percentage')] = 'percent'
    unit.loc[definitions.str.contains('per 1,000 Beneficiary Months', regex=False)] = 'per_1000_beneficiary_months'
    unit.loc[definitions.str.contains('per 100,000 Beneficiary Months', regex=False)] = 'per_100000_beneficiary_months'
    unit.loc[definitions.str.startswith('Ratio of Observed')] = 'ratio'
    if unit.eq('unknown').any():
        raise ValueError('Unrecognized rate definition; review units')
    silver['rate_unit'] = unit
    for field in BENCHMARKS:
        silver[field] = numeric(raw[field], field)
    if not raw.number_of_states_reporting.str.fullmatch(r'\d+').all():
        raise ValueError('Invalid number of states reporting')
    silver['number_of_states_reporting'] = raw.number_of_states_reporting.astype('int64')
    for field in ['state_rate_numeric'] + BENCHMARKS:
        if silver.loc[unit.eq('percent'), field].gt(100).any():
            raise ValueError(f'Percentage exceeds 100 in {field}')
    # CMS quartiles are ranked by performance, not ascending numeric value.
    higher = silver.measure_direction.eq('higher_is_better')
    if silver.loc[higher, 'bottom_quartile'].gt(silver.loc[higher, 'top_quartile']).any() or silver.loc[~higher, 'bottom_quartile'].lt(silver.loc[~higher, 'top_quartile']).any():
        raise ValueError('Quartile ordering conflicts with measure direction')
    silver = silver.sort_values(KEY).reset_index(drop=True)
    counts = lambda col: {str(k): int(v) for k, v in silver[col].value_counts().sort_index().items()}
    report = {'input_rows': len(raw), 'output_rows': len(silver), 'input_columns': len(raw.columns),
              'output_columns': len(silver.columns), 'key': KEY, 'duplicate_keys': 0,
              'raw_blank_counts': {c: int(raw[c].eq('').sum()) for c in raw},
              'state_rows': counts('cga_state'), 'program_rows': counts('reporting_program'),
              'status_rows': counts('state_rate_status'), 'unit_rows': counts('rate_unit'),
              'direction_rows': counts('measure_direction'), 'benchmark_inclusion_rows': counts('rate_used_in_calculating_state_mean_and_median'),
              'state_program_rows': {s: {p: int(n) for p, n in g.reporting_program.value_counts().items()} for s, g in silver.groupby('cga_state')},
              'numeric_rate_nulls': int(silver.state_rate_numeric.isna().sum()),
              'years': sorted(silver.core_set_year.unique().tolist()), 'validation': 'passed'}
    return silver, report


def run(source, output, report_path):
    raw = pd.read_csv(source, dtype=str, keep_default_na=False)
    silver, report = clean(raw)
    output.mkdir(parents=True, exist_ok=True)
    csv_path, parquet_path = (output / f'cms_core_sets_clean.{ext}' for ext in ['csv', 'parquet'])
    silver.to_csv(csv_path, index=False)
    with duckdb.connect() as connection:
        connection.register('silver', silver)
        connection.table('silver').write_parquet(str(parquet_path), compression='zstd')
        actual = connection.read_parquet(str(parquet_path))
        if actual.count('*').fetchone()[0] != len(silver):
            raise ValueError('Parquet row-count mismatch')
        expected = connection.sql('SELECT * FROM silver ORDER BY ' + ','.join(KEY)).df()
        actual_df = actual.order(','.join(KEY)).df()
        pd.testing.assert_frame_equal(expected, actual_df)
        report['parquet_schema'] = dict(zip(actual.columns, map(str, actual.types)))
    report.update({'built_at_utc': datetime.now(timezone.utc).isoformat(), 'source': str(source),
                   'source_sha256': digest(source), 'outputs': {str(p): digest(p) for p in [csv_path, parquet_path]},
                   'parquet_roundtrip': 'passed'})
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/processed/cms_quality_five_states.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/silver'))
    parser.add_argument('--report', type=Path, default=Path('reports/core_sets_cleaning.json'))
    args = parser.parse_args()
    result = run(args.source, args.output, args.report)
    print(json.dumps(result, indent=2))
