from unittest.mock import Mock, patch
import unittest

from services.euro_exact_rebuild_service import (
    BUILD_EXACT_CONFIRMATION,
    REBUILD_VERSION,
    SWAP_EXACT_CONFIRMATION,
    TARGET_IMPORT_KEYS,
    build_exact_shadows,
    swap_exact_shadows,
)
from services.euro_rebuild_service import (
    build_shadow_schema_statements,
    build_rollback_statement,
    build_swap_statement,
    retained_table_name,
    shadow_table_name,
)


class EuroExactRebuildServiceTests(unittest.TestCase):
    @patch(
        "services.euro_rebuild_service._mapped_source_columns",
        return_value=("key_code", "time_period", "obs_value", "compilation"),
    )
    @patch("services.euro_rebuild_service.inspect")
    def test_shadow_schema_removes_legacy_auto_increment_id(
        self,
        inspect_mock,
        _columns_mock,
    ):
        inspect_mock.return_value.get_columns.return_value = [
            {"name": "id", "type": "BIGINT"},
            {"name": "key_code", "type": "VARCHAR(255)"},
            {"name": "time_period", "type": "VARCHAR(50)"},
            {"name": "obs_value", "type": "DECIMAL(30,10)"},
            {"name": "compilation", "type": "VARCHAR(50)"},
        ]

        statements = build_shadow_schema_statements(
            Mock(),
            "EURO_FRAUD_LOSSES",
            "20260803_220000",
            version=REBUILD_VERSION,
        )

        self.assertEqual(3, len(statements))
        self.assertIn("MODIFY `id` BIGINT NOT NULL", statements[1])
        self.assertIn("DROP COLUMN `id`", statements[2])
        self.assertIn("MODIFY `compilation` TEXT NULL", statements[2])
        self.assertIn("ADD PRIMARY KEY (`key_code`, `time_period`)", statements[2])

    def test_v056_names_do_not_collide_with_v055_checkpoint(self):
        table = "euro_transactions_payments_systems"
        suffix = "20260803_220000"

        self.assertIn("shadow_v056", shadow_table_name(
            table,
            suffix,
            REBUILD_VERSION,
        ))
        self.assertIn("pre_v056", retained_table_name(
            table,
            suffix,
            REBUILD_VERSION,
        ))

    def test_v056_swap_and_rollback_cover_exact_targets(self):
        suffix = "20260803_220000"
        swap = build_swap_statement(
            TARGET_IMPORT_KEYS,
            suffix,
            version=REBUILD_VERSION,
        )
        rollback = build_rollback_statement(
            TARGET_IMPORT_KEYS,
            suffix,
            version=REBUILD_VERSION,
        )

        self.assertEqual(swap.count(" TO "), len(TARGET_IMPORT_KEYS) * 2)
        self.assertEqual(rollback.count(" TO "), len(TARGET_IMPORT_KEYS) * 2)
        self.assertIn("shadow_v056", swap)
        self.assertIn("pre_v056", rollback)

    def test_wrong_build_confirmation_stops_before_core_service(self):
        with patch(
            "services.euro_exact_rebuild_service.build_and_validate_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, BUILD_EXACT_CONFIRMATION):
                build_exact_shadows(
                    engine=Mock(),
                    backup_file="missing.sql",
                    confirmation="WRONG",
                    suffix="20260803_220000",
                )
        core.assert_not_called()

    def test_wrong_swap_confirmation_stops_before_core_service(self):
        with patch(
            "services.euro_exact_rebuild_service.swap_validated_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, SWAP_EXACT_CONFIRMATION):
                swap_exact_shadows(
                    engine=Mock(),
                    backup_file="missing.sql",
                    confirmation="WRONG",
                    suffix="20260803_220000",
                )
        core.assert_not_called()


if __name__ == "__main__":
    unittest.main()
