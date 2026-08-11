from pathlib import Path
import tempfile
import unittest

import pandas as pd

from services.euro_direct_debits_diagnostic_service import (
    classify_direct_debits_period_alignment,
    write_direct_debits_diagnostic,
)


class EuroDirectDebitsDiagnosticTests(unittest.TestCase):
    def test_classifies_collapsed_years_and_unexplained_differences(self):
        source = pd.DataFrame(
            [
                {"key_code": "A", "freq": "A", "time_period": "2024"},
                {"key_code": "H", "freq": "H", "time_period": "2024-S1"},
                {"key_code": "H", "freq": "H", "time_period": "2024-S2"},
                {"key_code": "Q", "freq": "Q", "time_period": "2024-Q1"},
                {"key_code": "Q", "freq": "Q", "time_period": "2024-Q2"},
                {"key_code": "NEW", "freq": "H", "time_period": "2025-S1"},
            ]
        )
        target = pd.DataFrame(
            [
                {"key_code": "A", "freq": "A", "time_period": "2024"},
                {"key_code": "H", "freq": "H", "time_period": "2024"},
                {"key_code": "Q", "freq": "Q", "time_period": "2024"},
                {"key_code": "OLD", "freq": "H", "time_period": "2023"},
            ]
        )

        result = classify_direct_debits_period_alignment(source, target, "YEAR")
        summary = result["summary"]

        self.assertEqual(1, summary["common_business_keys"])
        self.assertEqual(5, summary["source_only_rows"])
        self.assertEqual(4, summary["source_only_explained_by_year_collapse"])
        self.assertEqual(3, summary["target_only_rows"])
        self.assertEqual(2, summary["target_only_explained_by_detailed_source"])
        self.assertEqual("mixed_period_differences_require_review", summary["conclusion"])
        self.assertFalse(summary["database_write_performed"])

    def test_full_collapse_is_confirmed_and_report_is_local_only(self):
        source = pd.DataFrame(
            [
                {"KEY": "H", "FREQ": "H", "TIME_PERIOD": "2024-S1"},
                {"KEY": "H", "FREQ": "H", "TIME_PERIOD": "2024-S2"},
            ]
        )
        target = pd.DataFrame(
            [{"key_code": "H", "freq": "H", "time_period": "2024"}]
        )
        diagnostic = classify_direct_debits_period_alignment(source, target, "YEAR")

        self.assertEqual(
            "lossy_target_time_period_storage_confirmed",
            diagnostic["summary"]["conclusion"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            outputs = write_direct_debits_diagnostic(tmp, diagnostic)
            for path in outputs.values():
                self.assertTrue(Path(path).is_file())


if __name__ == "__main__":
    unittest.main()
