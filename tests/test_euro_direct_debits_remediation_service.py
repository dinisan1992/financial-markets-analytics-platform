from unittest.mock import Mock, patch
import unittest

from services.euro_direct_debits_remediation_service import (
    REMEDIATION_VERSION,
    build_direct_debits_rebuild_plan,
)


class EuroDirectDebitsRemediationTests(unittest.TestCase):
    @patch(
        "services.euro_direct_debits_remediation_service.build_shadow_schema_statements",
        return_value=(
            "CREATE TABLE `shadow` LIKE `active`",
            "ALTER TABLE `shadow` MODIFY `time_period` VARCHAR(20) NOT NULL",
        ),
    )
    @patch(
        "services.euro_direct_debits_remediation_service.get_macro_import",
        return_value={
            "table_name": "euro_direct_debits",
            "csv_path": "Direct debits.csv",
        },
    )
    def test_plan_is_inspectable_and_has_no_write_path(
        self,
        _contract_mock,
        schema_mock,
    ):
        diagnostic = {
            "summary": {
                "conclusion": "lossy_target_time_period_storage_confirmed",
                "source_rows": 121_564,
                "target_rows": 75_647,
                "target_period_type": "YEAR",
                "source_only_rows": 77_025,
                "target_only_rows": 31_108,
                "unexplained_source_only_rows": 0,
                "unexplained_target_only_rows": 0,
            }
        }

        plan = build_direct_debits_rebuild_plan(
            Mock(),
            "20260811_160000",
            diagnostic=diagnostic,
        )

        self.assertEqual(REMEDIATION_VERSION, plan["version"])
        self.assertEqual("YEAR", plan["current_time_period_type"])
        self.assertEqual("VARCHAR(20)", plan["proposed_time_period_type"])
        self.assertEqual(121_564, plan["expected_shadow_rows"])
        self.assertFalse(plan["write_path_enabled"])
        self.assertFalse(plan["database_write_performed"])
        self.assertFalse(plan["active_table_changed"])
        self.assertIn("MODIFY `time_period` VARCHAR(20)", plan["shadow_schema_statements"][1])
        schema_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
