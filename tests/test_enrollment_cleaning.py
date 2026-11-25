import unittest

import pandas as pd

from acquire_public_data import STATES
from clean_enrollment import COUNTS, clean


class EnrollmentCleaningTests(unittest.TestCase):
    def fixture(self):
        rows = []
        for state, name in STATES.items():
            for final, version, total in [("N", "P", "90"), ("Y", "U", "100")]:
                rows.append(dict(zip(COUNTS, ["80", "20", total, "", "30"])) | {
                    "cga_state": state, "state_abbreviation": state, "state_name": name,
                    "reporting_period": "202401", "final_report": final,
                    "preliminary_or_updated": version,
                })
        return pd.DataFrame(rows)

    def test_preliminary_exclusion_and_missing_adults(self):
        clean_data, report = clean(self.fixture())
        self.assertEqual(len(clean_data), 5)
        self.assertEqual(report["matched_combined_counts_changed"], 5)
        self.assertTrue(clean_data[COUNTS[3]].isna().all())
        self.assertTrue(clean_data[COUNTS[2]].eq(100).all())

    def test_duplicate_final_rejected(self):
        raw = self.fixture()
        duplicate = pd.concat([raw, raw.iloc[[1]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            clean(duplicate)

    def test_reconciliation_failure_rejected(self):
        raw = self.fixture()
        raw.loc[1, "total_medicaid_and_chip_enrollment"] = "101"
        with self.assertRaisesRegex(ValueError, "combined reported total"):
            clean(raw)

    def test_invalid_numeric_value_rejected(self):
        raw = self.fixture()
        raw.loc[1, "total_adult_medicaid_enrollment"] = "unknown"
        with self.assertRaisesRegex(ValueError, "Unexpected numeric value"):
            clean(raw)
