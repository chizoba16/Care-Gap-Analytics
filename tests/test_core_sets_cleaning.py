import unittest

import pandas as pd

from acquire_public_data import STATES
from clean_core_sets import clean, FLAGS


def fixture():
    return pd.DataFrame([dict(cga_state=code, state=name, domain='Test',
        reporting_program='Adult Core Set', measure_name='Test measure', measure_abbreviation='TEST',
        measure_type='Higher rates are better for this measure', rate_definition='Percentage tested',
        core_set_year='2024', population='Medicaid', methodology='Administrative', state_rate='0',
        number_of_states_reporting='5', mean='50', median='50', bottom_quartile='25', top_quartile='75',
        notes='', source='Synthetic test fixture', statespecific_comments='Test',
        rate_used_in_calculating_state_mean_and_median='Yes') for code, name in STATES.items()])


class CoreSetTests(unittest.TestCase):
    def test_flags_distinct_from_zero(self):
        raw = fixture()
        for i, flag in enumerate(FLAGS):
            raw.loc[i, ['state_rate', 'notes']] = [flag, 'Source explanation']
        silver, report = clean(raw)
        self.assertEqual(report['numeric_rate_nulls'], 4)
        self.assertEqual(silver.loc[silver.state_rate.eq('0'), 'state_rate_numeric'].iloc[0], 0)
        self.assertEqual(set(silver.state_rate_status), set(FLAGS.values()) | {'reported'})

    def test_unknown_flag_rejected(self):
        raw = fixture()
        raw.loc[0, 'state_rate'] = 'unknown'
        with self.assertRaises(ValueError):
            clean(raw)

    def test_duplicate_rejected_but_population_distinguished(self):
        raw = fixture()
        extra = raw.iloc[[0]].copy()
        with self.assertRaises(ValueError):
            clean(pd.concat([raw, extra], ignore_index=True))
        extra['population'] = 'Separate CHIP'
        self.assertEqual(len(clean(pd.concat([raw, extra], ignore_index=True))[0]), 6)

    def test_percentage_bound_and_nonpercentage(self):
        raw = fixture()
        raw.loc[0, 'state_rate'] = '125'
        with self.assertRaises(ValueError):
            clean(raw)
        raw.loc[0, 'rate_definition'] = 'Emergency Department Visits per 1,000 Beneficiary Months'
        self.assertEqual(clean(raw)[0].state_rate_numeric.max(), 125)

    def test_lower_is_better_quartiles(self):
        raw = fixture()
        raw.loc[0, 'measure_type'] = 'Lower rates are better for this measure'
        with self.assertRaises(ValueError):
            clean(raw)
        raw.loc[0, ['bottom_quartile', 'top_quartile']] = ['75', '25']
        self.assertEqual(clean(raw)[1]['direction_rows']['lower_is_better'], 1)
