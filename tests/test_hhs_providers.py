import tempfile
import unittest
from pathlib import Path

import duckdb

from clean_hhs_providers import macros, enrollment, spending, validate_artifacts


class HHSProviderTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect()
        macros(self.con)

    def tearDown(self):
        self.con.close()

    def test_identifiers_and_codes(self):
        self.assertEqual(self.con.sql("SELECT valid_npi('1234567893'), valid_npi('1234567890'), valid_npi(NULL), valid_ndc('00006057761'), valid_ndc('88888888888'), valid_hcpcs('20'), valid_hcpcs('99213')").fetchone(),
                         (True, False, False, True, False, False, True))

    def test_temporal_link_and_national_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / 'enrollment.parquet'
            # NY provider overlaps CA in February, not January; duplicates/plan segments don't multiply claims.
            self.con.sql("""SELECT * FROM (VALUES
                ('1234567893','NY',DATE '2018-01-01',DATE '2018-12-31','03','1'),
                ('1234567893','CA',DATE '2018-02-01',DATE '2018-02-28','79','1'),
                ('1234567893','NY',DATE '2018-01-01',DATE '2018-12-31','03','2'),
                ('1234567893','NJ',DATE '2019-01-01',NULL,'03','1'),
                ('1234567893','MD',DATE '2020-01-01',DATE '2019-12-31','03','1'),
                ('1234567893','VA',DATE '2018-01-01',DATE '2018-01-31','03','1'),
                ('1234567893','PA',DATE '2018-03-01',DATE '2018-03-31','03','1'))
                t(NPI,STATE_CD,ENRL_START_DT,ENRL_END_DT,ENRL_STATUS_CD,ENRL_PLAN_CD)""").write_parquet(str(p))
            _, result = enrollment(self.con,p,root)
            self.assertEqual(result['five_state_rows'],6)
            self.assertEqual(self.con.sql("SELECT len(month_evidence(states,1)) FROM provider_map").fetchone(),(2,))
            self.assertEqual(self.con.sql("SELECT month_evidence(states,3)[1].state FROM provider_map").fetchone(),('NY',))
            self.assertEqual(self.con.sql("SELECT month_evidence(states,72)[1].state, (month_evidence(states,72)[1].open_end & (1::HUGEINT<<72))<>0 FROM provider_map").fetchone(),('NJ',True))
            claims = root / 'claims.parquet'
            self.con.sql("""SELECT * FROM (VALUES
                ('1234567893',NULL::VARCHAR,'99213','2018-02',12,12,50.0),
                ('1234567893',NULL,'99213','2018-04',12,13,100.0),
                ('1234567893',NULL,'20','2018-04',12,12,1000000000.0),
                (NULL,NULL,'99213','2018-04',12,12,20.0))
                t(BILLING_PROVIDER_NPI_NUM,SERVICING_PROVIDER_NPI_NUM,HCPCS_CODE,CLAIM_FROM_MONTH,TOTAL_PATIENTS,TOTAL_CLAIM_LINES,TOTAL_PAID)""").write_parquet(str(claims))
            _, stats = spending(self.con,'hcpcs',claims,root)
            self.assertEqual(stats['rows'],4)
            self.assertEqual(stats['proxy_cells'],1)
            self.assertEqual(stats['extreme_paid_rows'],1)
            self.assertEqual(stats['invalid_code_rows'],1)
            result = validate_artifacts(root, {'spending': {'hcpcs':stats}})
            self.assertEqual(result['spending']['hcpcs']['export_reconciliation'],'passed')


if __name__ == '__main__':
    unittest.main()
