"""Validate CMS-64 worksheet line items and isolate reported net totals."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from acquire_public_data import STATES
from acquire_spending_data import YEARS
from clean_enrollment import digest

GRAIN = ['state', 'fiscal_year', 'program']
KEY = GRAIN + ['source_row']
MONEY = ['total_computable_usd', 'federal_share_usd', 'state_share_usd']
REQUIRED = KEY + MONEY + ['source_category', 'source_workbook', 'source_sheet']
PROGRAMS = {'medical_assistance': 'MAP', 'administration': 'ADM'}


def typed(raw):
    if set(REQUIRED) - set(raw.columns):
        raise ValueError('Required CMS-64 columns missing')
    if raw[REQUIRED].apply(lambda c: c.str.strip().eq('')).any().any():
        raise ValueError('Blank required source values')
    x = raw.copy()
    for c in MONEY + ['fiscal_year', 'source_row']:
        if not x[c].str.fullmatch(r'-?\d+').all():
            raise ValueError(f'Expected whole-dollar/integer values: {c}')
        x[c] = x[c].astype('int64')
    if not x.state.isin(STATES).all() or not x.program.isin(PROGRAMS).all() or not x.fiscal_year.isin(YEARS).all():
        raise ValueError('Invalid state, program or fiscal year')
    if not x.source_sheet.eq(x.program.map(PROGRAMS) + ' - ' + x.state.map(STATES)).all():
        raise ValueError('Source sheet identity mismatch')
    if not x.source_workbook.eq('FY ' + x.fiscal_year.astype(str) + ' FMR NET EXPENDITURES.xlsx').all():
        raise ValueError('Source workbook identity mismatch')
    if x.source_row.lt(8).any() or x.duplicated(KEY).any():
        raise ValueError('Invalid or duplicate worksheet row key')
    # Python integers avoid fixed-width overflow in equality checks.
    if any(t != f + s for t, f, s in x[MONEY].itertuples(index=False, name=None)):
        raise ValueError('Funding split does not reconcile')
    return x


def clean(raw_detail, raw_totals):
    detail, totals = typed(raw_detail), typed(raw_totals)
    expected = {(s, y, p) for s in STATES for y in YEARS for p in PROGRAMS}
    for x in [detail, totals]:
        if set(x[GRAIN].itertuples(index=False, name=None)) != expected:
            raise ValueError('Incomplete state/year/program coverage')
    if totals.duplicated(GRAIN).any() or not totals.source_category.str.strip().eq('Total Net Expenditures').all():
        raise ValueError('Reported totals must be one exact net line per sheet')
    detail['line_role'] = 'outside_main_net_total'
    for key, group in detail.groupby(GRAIN):
        label = group.source_category.str.strip()
        balance, net = group.loc[label.eq('Balance')], group.loc[label.eq('Total Net Expenditures')]
        if len(balance) != 1 or len(net) != 1:
            raise ValueError(f'Missing or repeated balance/net line: {key}')
        b, n = int(balance.source_row.iloc[0]), int(net.source_row.iloc[0])
        if b >= n:
            raise ValueError(f'Invalid worksheet order: {key}')
        component = group.loc[group.source_row.lt(b)]
        adjustments = group.loc[group.source_row.gt(b) & group.source_row.lt(n)]
        if component.empty or adjustments.empty:
            raise ValueError(f'Incomplete main section: {key}')
        for c in MONEY:
            if sum(map(int, component[c])) != int(balance[c].iloc[0]):
                raise ValueError(f'Balance reconciliation failed: {key}, {c}')
            if int(balance[c].iloc[0]) + sum(map(int, adjustments[c])) != int(net[c].iloc[0]):
                raise ValueError(f'Net reconciliation failed: {key}, {c}')
        detail.loc[component.index, 'line_role'] = 'main_balance_component'
        detail.loc[balance.index, 'line_role'] = 'main_balance_subtotal'
        detail.loc[adjustments.index, 'line_role'] = 'main_net_adjustment'
        detail.loc[net.index, 'line_role'] = 'main_reported_net_total'
    selected = detail.loc[detail.line_role.eq('main_reported_net_total'), REQUIRED].sort_values(KEY).reset_index(drop=True)
    pd.testing.assert_frame_equal(selected, totals[REQUIRED].sort_values(KEY).reset_index(drop=True))
    detail['include_in_main_net_sum'] = detail.line_role.isin(['main_balance_component', 'main_net_adjustment'])
    totals['line_role'] = 'main_reported_net_total'
    detail = detail.sort_values(KEY).reset_index(drop=True)
    totals = totals.sort_values(KEY).reset_index(drop=True)
    report = {'input_detail_rows': len(raw_detail), 'output_detail_rows': len(detail), 'output_total_rows': len(totals),
              'detail_key': KEY, 'total_key': GRAIN, 'years': list(YEARS), 'states': sorted(STATES),
              'source_category_labels': int(detail.source_category.nunique()),
              'duplicate_category_keys_excess_rows': int(detail.duplicated(GRAIN + ['source_category']).sum()),
              'negative_counts': {c: int(detail[c].lt(0).sum()) for c in MONEY},
              'zero_counts': {c: int(detail[c].eq(0).sum()) for c in MONEY},
              'line_role_counts': {k: int(v) for k, v in detail.line_role.value_counts().items()},
              'funding_rows_reconciled': len(detail), 'sheets_balance_reconciled': len(totals),
              'sheets_net_reconciled': len(totals), 'reported_total_extract_matches': len(totals),
              'total_rows_by_state': {k: int(v) for k, v in totals.state.value_counts().items()},
              'validation': 'passed'}
    return detail, totals, report


def run(detail_path, totals_path, output, report_path):
    inputs = [detail_path, totals_path]
    detail, totals, report = clean(*(pd.read_csv(p, dtype=str, keep_default_na=False) for p in inputs))
    output.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name, frame in [('detail', detail), ('reported_totals', totals)]:
        csv_path = output / f'cms64_{name}_clean.csv'
        parquet_path = output / f'cms64_{name}_clean.parquet'
        frame.to_csv(csv_path, index=False)
        with duckdb.connect() as con:
            con.register('silver', frame)
            con.table('silver').write_parquet(str(parquet_path), compression='zstd')
            actual = con.read_parquet(str(parquet_path))
            order = ','.join(KEY)
            pd.testing.assert_frame_equal(con.sql(f'SELECT * FROM silver ORDER BY {order}').df(), actual.order(order).df())
            report[name + '_parquet_schema'] = dict(zip(actual.columns, map(str, actual.types)))
        outputs.extend([csv_path, parquet_path])
    report.update({'built_at_utc': datetime.now(timezone.utc).isoformat(),
                   'inputs': {str(p): digest(p) for p in inputs}, 'outputs': {str(p): digest(p) for p in outputs},
                   'parquet_roundtrip': 'passed'})
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--detail', type=Path, default=Path('data/processed/cms64_five_state_detail.csv'))
    parser.add_argument('--totals', type=Path, default=Path('data/processed/cms64_five_state_reported_totals.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/silver'))
    parser.add_argument('--report', type=Path, default=Path('reports/cms64_cleaning.json'))
    args = parser.parse_args()
    print(json.dumps(run(args.detail, args.totals, args.output, args.report), indent=2))
