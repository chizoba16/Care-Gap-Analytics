import tempfile
import unittest
from pathlib import Path
import pandas as pd
from pipeline import continuous_coverage, build_cohort, metrics

class PipelineTests(unittest.TestCase):
    def test_coverage_gap_not_bridged(self):
        self.assertFalse(continuous_coverage([(2015, 2016), (2017, 2020)], pd.Timestamp('2015-01-01'), pd.Timestamp('2019-01-01')))
        self.assertTrue(continuous_coverage([(2015, 2017), (2017, 2020)], pd.Timestamp('2016-01-01'), pd.Timestamp('2019-01-01')))

    def test_window_boundaries_and_infant_exclusion(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder)
            pd.DataFrame([dict(Id='a', BIRTHDATE='2010-01-01', DEATHDATE=None, GENDER='F', RACE='x'),dict(Id='baby', BIRTHDATE='2016-06-01', DEATHDATE=None, GENDER='F', RACE='x')]).to_csv(raw/'patients.csv',index=False)
            pd.DataFrame([dict(Id='m', NAME='Medicaid')]).to_csv(raw/'payers.csv',index=False)
            pd.DataFrame([dict(PATIENT=k,START_YEAR=2010,END_YEAR=2020,PAYER='m') for k in ['a','baby']]).to_csv(raw/'payer_transitions.csv',index=False)
            pd.DataFrame([dict(Id=str(i),PATIENT='a',START=date,ENCOUNTERCLASS=kind) for i,(date,kind) in enumerate([('2016-01-02','wellness'),('2017-01-01','emergency'),('2017-04-01','emergency'),('2020-01-01','ambulatory')])]).to_csv(raw/'encounters.csv',index=False)
            c=build_cohort(raw,'2017-01-01')
            self.assertEqual(len(c),1)
            self.assertEqual(c.iloc[0].wellness_visits,1)
            self.assertEqual(c.iloc[0].ed_visits,0)
            self.assertEqual(c.iloc[0].ed_next_90d,1)
            self.assertEqual(c.iloc[0].well_care_gap_proxy,0)

    def test_single_class_metrics(self):
        self.assertIsNone(metrics([0,0],[.2,.1])['roc_auc'])
        self.assertIsNone(metrics([0,0],[.2,.1])['recall_at_10pct'])

if __name__=='__main__':
    unittest.main()
