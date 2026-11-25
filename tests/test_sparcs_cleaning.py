import csv
import tempfile
import unittest
from pathlib import Path

import duckdb

from clean_sparcs import COLUMNS, clean


def fixture(**changes):
    row = dict(zip(COLUMNS, ['NYC','Kings','7002054','001438','Example Hospital','0-17','112','F','Other Race','Unknown','120+','Emergency','Home or Self Care','2024','PNL001','Example diagnosis','','','640','Example DRG','15','Example MDC','1','Minor','Minor','Medical','Medicaid','','','UNKN','Y','100.50','25.01']))
    return row | changes


class SparcsTests(unittest.TestCase):
    def check(self, records, fn):
        with tempfile.TemporaryDirectory() as directory, duckdb.connect() as con:
            path=Path(directory)/'fixture.csv'
            with path.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=COLUMNS);writer.writeheader();writer.writerows(records)
            clean(con,path)
            fn(con)

    def test_censored_stay_and_exact_money(self):
        def verify(c):
            self.assertEqual(c.sql('SELECT stay_days_exact,stay_days_lower_bound,stay_right_censored,birth_weight_status,permanent_facility_id,cost_exceeds_charge,zero_estimated_cost FROM silver').fetchone(),(None,120,True,'unknown','001438',False,False))
        self.check([fixture()],verify)

    def test_redacted_and_duplicate_rows_preserved(self):
        row=fixture(facility_name='Redacted for Confidentiality',hospital_county='',health_service_area='',permanent_facility_id='',operating_certificate_number='',zip_code='',age_group='30-49',birth_weight='',length_of_stay='1',total_charges='.05',total_costs='.11')
        def verify(c):
            self.assertEqual(c.sql('SELECT count(*),bool_and(facility_redacted),bool_and(cost_exceeds_charge),min(age_cohort) FROM silver').fetchone(),(2,True,True,'adult'))
        self.check([row,row],verify)

    def test_wrong_payer_and_invalid_stay_rejected(self):
        for row in [fixture(payment_typology_1='Medicare'),fixture(length_of_stay='0'),fixture(total_costs='-1'),fixture(ccsr_procedure_code='PGN002')]:
            with self.assertRaises(ValueError):
                self.check([row],lambda c: None)
