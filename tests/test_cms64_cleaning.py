import unittest

import pandas as pd

from clean_cms64 import clean, STATES, YEARS, PROGRAMS


def fixture():
    rows = []
    for state, name in STATES.items():
        for year in YEARS:
            for program, prefix in PROGRAMS.items():
                for row, category, total, federal in [(8, 'Service', 100, 60), (9, 'Balance', 100, 60),
                        (10, 'Collections', -10, -6), (11, 'Total Net Expenditures', 90, 54),
                        (12, 'Service', 5, 3)]:
                    rows.append(dict(state=state, fiscal_year=str(year), program=program, source_row=str(row),
                        source_category=category, total_computable_usd=str(total), federal_share_usd=str(federal),
                        state_share_usd=str(total-federal), source_workbook=f'FY {year} FMR NET EXPENDITURES.xlsx',
                        source_sheet=f'{prefix} - {name}'))
    raw = pd.DataFrame(rows)
    return raw, raw.loc[raw.source_category.eq('Total Net Expenditures')].copy()


class CMS64Tests(unittest.TestCase):
    def test_preserve_adjustment_and_repeated_labels(self):
        detail, totals, report = clean(*fixture())
        self.assertEqual(len(detail), 400)
        self.assertEqual(len(totals), 80)
        self.assertEqual(report['duplicate_category_keys_excess_rows'], 80)
        self.assertEqual(detail.loc[detail.include_in_main_net_sum, 'total_computable_usd'].sum(), totals.total_computable_usd.sum())
        self.assertEqual(detail.loc[detail.source_category.eq('Collections'), 'total_computable_usd'].min(), -10)

    def test_funding_split(self):
        raw, totals = fixture()
        raw.loc[0, 'state_share_usd'] = '41'
        with self.assertRaisesRegex(ValueError, 'Funding split'):
            clean(raw, totals)

    def test_balance_mismatch_despite_funding_reconciliation(self):
        raw, totals = fixture()
        raw.loc[0, ['total_computable_usd', 'state_share_usd']] = ['101', '41']
        with self.assertRaisesRegex(ValueError, 'Balance reconciliation'):
            clean(raw, totals)

    def test_net_mismatch(self):
        raw, totals = fixture()
        raw.loc[2, ['total_computable_usd', 'state_share_usd']] = ['-11', '-5']
        with self.assertRaisesRegex(ValueError, 'Net reconciliation'):
            clean(raw, totals)

    def test_duplicate_worksheet_line(self):
        raw, totals = fixture()
        with self.assertRaisesRegex(ValueError, 'duplicate worksheet'):
            clean(pd.concat([raw, raw.iloc[[0]]]), totals)

    def test_total_extract_mismatch(self):
        raw, totals = fixture()
        totals.iloc[0, totals.columns.get_loc('total_computable_usd')] = '91'
        totals.iloc[0, totals.columns.get_loc('state_share_usd')] = '37'
        with self.assertRaises(AssertionError):
            clean(raw, totals)
